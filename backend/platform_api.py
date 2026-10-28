"""LabourLawyer platform APIs.

This module deliberately uses the Python standard library SQLite driver so the
case-management foundation stays lightweight and can run alongside the existing
document and local-LLM services.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field


DATA_DIR = Path(os.getenv("LABOURLAWYER_DATA_DIR", Path(__file__).parent / "data"))
DB_PATH = DATA_DIR / "labourlawyer.db"
router = APIRouter(prefix="/api/platform", tags=["平台能力"])


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_database() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                client_name TEXT NOT NULL,
                employer_name TEXT NOT NULL,
                region TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT '案情梳理',
                dispute_amount REAL NOT NULL DEFAULT 0,
                deadline TEXT,
                summary TEXT NOT NULL DEFAULT '',
                evidence_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deadlines (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                title TEXT NOT NULL,
                due_at TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT '材料任务',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_cases_stage ON cases(stage);
            CREATE INDEX IF NOT EXISTS idx_deadlines_due_at ON deadlines(due_at);
            """
        )


init_database()


CaseStage = Literal["案情梳理", "材料准备", "待提交", "审理中", "已结案"]


class CaseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=80)
    client_name: str = Field(min_length=1, max_length=60)
    employer_name: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=60)
    dispute_amount: float = Field(default=0, ge=0, le=1_000_000_000)
    deadline: date | None = None
    summary: str = Field(default="", max_length=4000)


class CaseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=2, max_length=80)
    employer_name: str | None = Field(default=None, min_length=2, max_length=120)
    region: str | None = Field(default=None, min_length=2, max_length=60)
    stage: CaseStage | None = None
    dispute_amount: float | None = Field(default=None, ge=0, le=1_000_000_000)
    deadline: date | None = None
    summary: str | None = Field(default=None, max_length=4000)


class DeadlineCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=120)
    due_at: datetime
    kind: Literal["法定时限", "材料任务", "开庭", "内部提醒"] = "材料任务"


def serialize_case(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["links"] = {
        "self": f"/api/platform/cases/{item['id']}",
        "deadlines": f"/api/platform/cases/{item['id']}/deadlines",
    }
    return item


@router.get("/summary")
def dashboard_summary() -> dict[str, Any]:
    today = date.today().isoformat()
    with connection() as db:
        active = db.execute("SELECT COUNT(*) FROM cases WHERE stage != '已结案'").fetchone()[0]
        total = db.execute("SELECT COALESCE(SUM(dispute_amount), 0) FROM cases WHERE stage != '已结案'").fetchone()[0]
        due = db.execute("SELECT COUNT(*) FROM deadlines WHERE completed = 0 AND date(due_at) >= date(?) AND date(due_at) <= date(?, '+7 day')", (today, today)).fetchone()[0]
    return {"active_cases": active, "active_dispute_amount": total, "deadlines_next_7_days": due, "generated_at": utc_now()}


@router.get("/cases")
def list_cases(q: str = Query(default="", max_length=80), stage: CaseStage | None = None, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if q:
        clauses.append("(id LIKE ? OR title LIKE ? OR client_name LIKE ? OR employer_name LIKE ?)")
        term = f"%{q}%"
        values.extend([term, term, term, term])
    if stage:
        clauses.append("stage = ?")
        values.append(stage)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as db:
        rows = db.execute(f"SELECT * FROM cases{where} ORDER BY updated_at DESC LIMIT ?", [*values, limit]).fetchall()
    return {"items": [serialize_case(row) for row in rows], "count": len(rows)}


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate) -> dict[str, Any]:
    now = utc_now()
    case_id = f"PL-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"
    with connection() as db:
        db.execute(
            "INSERT INTO cases (id,title,client_name,employer_name,region,dispute_amount,deadline,summary,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (case_id, payload.title, payload.client_name, payload.employer_name, payload.region, payload.dispute_amount, payload.deadline.isoformat() if payload.deadline else None, payload.summary, now, now),
        )
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return serialize_case(row)


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    with connection() as db:
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="案件不存在")
    return serialize_case(row)


@router.patch("/cases/{case_id}")
def update_case(case_id: str, payload: CaseUpdate) -> dict[str, Any]:
    changes = payload.model_dump(exclude_unset=True)
    if "deadline" in changes and changes["deadline"] is not None:
        changes["deadline"] = changes["deadline"].isoformat()
    if not changes:
        return get_case(case_id)
    changes["updated_at"] = utc_now()
    assignments = ", ".join(f"{key} = ?" for key in changes)
    with connection() as db:
        result = db.execute(f"UPDATE cases SET {assignments} WHERE id = ?", [*changes.values(), case_id])
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="案件不存在")
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return serialize_case(row)


@router.get("/cases/{case_id}/deadlines")
def list_deadlines(case_id: str) -> dict[str, Any]:
    with connection() as db:
        if not db.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone():
            raise HTTPException(status_code=404, detail="案件不存在")
        rows = db.execute("SELECT * FROM deadlines WHERE case_id = ? ORDER BY due_at", (case_id,)).fetchall()
    return {"items": [dict(row) for row in rows], "count": len(rows)}


@router.post("/cases/{case_id}/deadlines", status_code=status.HTTP_201_CREATED)
def create_deadline(case_id: str, payload: DeadlineCreate) -> dict[str, Any]:
    deadline_id = uuid.uuid4().hex
    with connection() as db:
        if not db.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone():
            raise HTTPException(status_code=404, detail="案件不存在")
        db.execute("INSERT INTO deadlines (id,case_id,title,due_at,kind,created_at) VALUES (?,?,?,?,?,?)", (deadline_id, case_id, payload.title, payload.due_at.isoformat(), payload.kind, utc_now()))
        row = db.execute("SELECT * FROM deadlines WHERE id = ?", (deadline_id,)).fetchone()
    return dict(row)


@router.get("/jurisdictions")
def jurisdictions() -> dict[str, Any]:
    return {
        "items": [
            {"province": "浙江", "cities": ["杭州", "宁波", "温州", "嘉兴", "绍兴"], "templates": ["仲裁申请书", "证据清单"]},
            {"province": "广东", "cities": ["广州", "深圳", "佛山", "东莞", "珠海"], "templates": ["仲裁申请书", "证据清单"]},
        ]
    }
