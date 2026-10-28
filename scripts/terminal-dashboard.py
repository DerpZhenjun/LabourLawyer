"""Live terminal panels, read-only job monitoring, and published result summaries.

Standard library only. Worker logs and structured events are retained on D drive.
"""
import argparse
from collections import deque
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from terminal_progress import ENV, emit
from province_documents import PROVINCE_DOCUMENTS

RUNTIME = ROOT / '.runtime/terminal/runs'
REPORTS = ROOT / 'templates/_reports'
ACTIVE = {'running', 'queued', 'reviewing'}
LABELS = {'capture': 'CAPTURE', 'browser': 'BROWSER', 'model': 'UBUNTU AI',
          'download': 'DOWNLOAD', 'publish': 'PUBLISH', 'report': 'REPORT',
          'report_check': 'REPORT AI', 'vision': 'AI CHECK', 'materials': 'MATERIALS',
          'workflows': 'WORKFLOWS', 'probe': 'CONNECT', 'job': 'JOB'}
REGION_LABELS = {'fresh':'本次取得','acquired':'指南已取得','historical':'沿用历史','not_detected':'尚未取得',
                 'failed':'失败','blocked':'受阻','stalled':'需重试','step_limit':'操作到上限',
                 'budget_exhausted':'时间到上限','complete':'已完成','cached':'复用结果',
                 'success':'已完成','success_with_warnings':'有待核实'}
ANSI = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))')


def clean(value):
    text = ANSI.sub('', str(value))
    return ''.join(c if ord(c) >= 32 and ord(c) != 127 else ' ' for c in text)


def cells(value):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in value)


def fit(value, width):
    text = clean(value); result = ''; used = 0
    for c in text:
        size = cells(c)
        if used + size > max(0, width): break
        result += c; used += size
    return result + ' ' * max(0, width - used)


def read_json(path):
    try: return json.loads(Path(path).read_text('utf-8-sig'))
    except (OSError, ValueError): return {}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf8'); temp.replace(path)


def name(slug):
    return PROVINCE_DOCUMENTS.get(str(slug).lower(), {}).get('name', slug)


class Journal:
    def __init__(self, path): self.path = Path(path); self.offset = 0; self.partial = b''
    def poll(self):
        try:
            if self.path.stat().st_size < self.offset: self.offset = 0; self.partial = b''
            with self.path.open('rb') as f:
                f.seek(self.offset); data = f.read(); self.offset = f.tell()
        except OSError: return []
        lines = (self.partial + data).split(b'\n'); self.partial = lines.pop()
        output = []
        for line in lines:
            try:
                event = json.loads(line.decode('utf8'))
                if isinstance(event, dict): output.append(event)
            except (ValueError, UnicodeError): pass
        return output


class View:
    def __init__(self, title):
        self.title = title; self.state = 'running'; self.started = time.time(); self.phase = 'job'
        self.current = None; self.total = None; self.province = ''; self.message = '准备任务'
        self.url = ''; self.output = ''; self.step = None; self.max_steps = None
        self.waits = {}; self.model_ok = 0; self.model_failed = 0; self.cached = 0
        self.regions = {}; self.events = deque(maxlen=5); self.logs = deque(maxlen=3)
        self.counts = {}; self.error = ''; self.model_timeout = None
        self.saved = False; self.operation_wait = None

    def apply(self, e):
        phase = e.get('phase', 'job'); state = e.get('state', 'running')
        if e.get('kind') == 'region':
            self.regions[e.get('province', '')] = e.get('region_state', state)
        if 'completed' in e: self.current = e['completed']
        if 'total' in e: self.total = e['total']
        if e.get('province'): self.province = e['province']
        if e.get('output'): self.output = e['output']
        if e.get('url'): self.url = e['url']
        if 'counts' in e: self.counts = e['counts']
        if phase == 'job' and state not in ACTIVE:
            self.state = state; self.error = e.get('error', ''); self.waits.clear(); self.operation_wait = None
        if phase == 'browser':
            self.operation_wait = e if state == 'waiting' else None
        # Calls can overlap: one completion must not hide another waiting call.
        if phase == 'model':
            key = e.get('call_id') or str(e.get('pid', 'model'))
            if state == 'waiting': self.waits[key] = e
            elif state in ('completed','failed'):
                self.waits.pop(key, None)
                if state == 'completed': self.model_ok += 1
                elif state == 'failed': self.model_failed += 1
        if state == 'cached': self.cached += e.get('count', 1)
        self.phase = phase
        if 'step' in e: self.step = e['step']; self.max_steps = e.get('max_steps')
        elif phase not in ('browser','model'): self.step = None; self.max_steps = None
        self.message = e.get('message') or e.get('action') or self.message
        if e.get('error'): self.error = e['error']
        if e.get('message') or e.get('action'):
            stamp = datetime.fromtimestamp(e.get('at', time.time())).strftime('%H:%M:%S')
            self.events.append(f"{stamp} {LABELS.get(phase, phase.upper())} / {name(e.get('province', ''))} {self.message}")

    def render(self, width=100, height=36, details=False):
        width = max(44, width); inner = width - 4
        rows = [f'LA / {self.title} / {self.state.upper()}',
                f"{'SAVED RESULT' if self.saved else 'ELAPSED '+str(int(time.time()-self.started))+'s'}   PHASE {LABELS.get(self.phase, self.phase.upper())}"]
        if self.current is not None and self.total:
            # This is an observed counter, not an invented ETA or time percentage.
            bar_size = max(8, min(30, inner - 26)); ratio = max(0, min(1, self.current / self.total))
            filled = int(bar_size * ratio)
            rows.append(f"PROGRESS [{'='*filled}{'.'*(bar_size-filled)}] {self.current}/{self.total} 已处理")
        else: rows.append('PROGRESS [~] 等待可计数结果')
        step = f'   STEP {self.step}/{self.max_steps}（操作上限）' if self.step is not None else ''
        rows.extend([f'NOW {name(self.province) or "--"}{step}', f'ACTION {self.message}'])
        if self.operation_wait:
            waiting=self.operation_wait
            elapsed=int(max(0,time.time()-waiting.get('at',time.time())))
            rows.append(f"[~] BROWSER WAIT 等待 {elapsed}s / 超时 {waiting.get('timeout_seconds','?')}s")
        if self.waits:
            waiting = max(self.waits.values(), key=lambda e: e.get('at', 0))
            elapsed = int(max(0, time.time() - waiting.get('at', time.time())))
            rows.append(f"[*] Qwen3.8:27B / 10.66.66.1  等待 {elapsed}s / 超时 {waiting.get('timeout_seconds', '?')}s  ({len(self.waits)} 调用)")
        elif self.saved: rows.append('[*] Qwen3.8:27B / Ubuntu   当前显示保存结果')
        else: rows.append(f"[*] Qwen3.8:27B / Ubuntu   OK {self.model_ok}   ERROR {self.model_failed}   CACHE {self.cached}")
        if self.url: rows.append('URL ' + self.url)
        if self.counts: rows.append('COUNTS ' + '   '.join(f'{k}={v}' for k, v in self.counts.items()))
        rows.append('─' * inner)
        if self.regions:
            statuses = {'fresh': '[+]', 'acquired': '[+]', 'historical': '[~]', 'not_detected': '[!]',
                        'failed': '[x]', 'complete': '[+]', 'cached': '[=]', 'running': '[>]'}
            column = max(1, inner // 29); cw = inner // column
            items = [f"{statuses.get(s,'[!]')} {name(p)}  {REGION_LABELS.get(s,s)}" for p, s in self.regions.items()]
            max_rows = len(items) if details else max(1, height - len(rows) - 13)
            for start in range(0, min(len(items), max_rows * column), column):
                rows.append(''.join(fit(item, cw) for item in items[start:start + column]))
            if len(items) > max_rows * column: rows.append(f'... 其余 {len(items)-max_rows*column} 项见结束结果 / summary')
        else: rows.append('REGIONS 暂无完成结果')
        rows.extend(['─' * inner, 'ACTIVITY'])
        rows.extend(self.events or ['等待程序事件…'])
        if self.error: rows.append('[!] ' + self.error)
        if self.output: rows.append('OUTPUT ' + self.output)
        if self.logs: rows.extend(['LOG (完整日志保存在运行目录)', *self.logs])
        if not details and len(rows) > max(1, height - 3):
            rows = rows[:max(1, height - 4)] + ['... 完整结果保存在运行目录 / summary']
        rows.append('Ctrl+C：运行面板停止本次任务；监控面板只退出查看')
        return '\n'.join(['┌' + '─' * (width - 2) + '┐'] +
                         ['│ ' + fit(row, inner) + ' │' for row in rows] +
                         ['└' + '─' * (width - 2) + '┘'])


class Screen:
    def __init__(self, plain=False):
        self.live = sys.stdout.isatty() and not plain
        self.handle = None; self.mode = None
        self.last_frame = None
        if self.live and os.name == 'nt':
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.GetStdHandle.restype = wintypes.HANDLE
            kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            handle = kernel.GetStdHandle(-11); mode = wintypes.DWORD()
            if kernel.GetConsoleMode(handle, ctypes.byref(mode)) and kernel.SetConsoleMode(handle, mode.value | 4):
                self.handle, self.mode, self.kernel = handle, mode.value, kernel
            else: self.live = False
        if self.live: print('\x1b[?1049h\x1b[?25l', end='', flush=True)
    def draw(self, view):
        if not self.live: return
        size = shutil.get_terminal_size((100, 36))
        panel = view.render(max(44,size.columns-1), max(6,size.lines-1))
        if panel == self.last_frame: return
        self.last_frame = panel
        # Color stays out of result files. The complete final summary remains scrollable.
        color = '31' if view.state in ('failed', 'interrupted', 'review_incomplete') else '33' if view.state in ('complete_with_gaps', 'incomplete') else '36'
        for icon, code in (('[+]','32'),('[=]','32'),('[!]','33'),('[~]','33'),('[x]','31')):
            panel = panel.replace(icon, f'\x1b[{code}m'+icon+f'\x1b[{color}m')
        print(f'\x1b[H\x1b[{color}m' + panel + '\x1b[0m\x1b[J', end='', flush=True)
    def close(self):
        if self.live:
            print('\x1b[0m\x1b[?25h\x1b[?1049l', end='', flush=True)
            if self.handle is not None: self.kernel.SetConsoleMode(self.handle, self.mode)
            self.live = False


def finish_state(view, code):
    if code != 0: return 'failed'
    if view.state in ('failed', 'incomplete', 'review_incomplete', 'interrupted', 'complete_with_gaps'): return view.state
    if any(s in ('historical', 'not_detected', 'failed', 'blocked', 'stalled', 'step_limit', 'budget_exhausted') for s in view.regions.values()): return 'complete_with_gaps'
    if any(s not in ('fresh','acquired','complete','cached','success','success_with_warnings') for s in view.regions.values()): return 'incomplete'
    return 'complete'


def stop_worker(process):
    """Bounded cleanup of this launched child; never target other services."""
    if process.poll() is not None: return ''
    warnings=[]
    try:
        if os.name=='nt':process.send_signal(signal.CTRL_BREAK_EVENT)
        else:process.terminate()
        process.wait(timeout=5)
        return ''
    except (OSError,subprocess.TimeoutExpired):pass
    if os.name=='nt' and process.poll() is None:
        try:
            ended=subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
            if ended.returncode:warnings.append('子进程树的结束状态未确认')
        except (OSError,subprocess.TimeoutExpired):warnings.append('结束子进程树超时或失败')
    if process.poll() is None:
        try:process.kill();process.wait(timeout=3)
        except (OSError,subprocess.TimeoutExpired):warnings.append('本次工作进程的结束状态未确认')
    return '；'.join(warnings)


def run(command, title, plain=False):
    if not command: raise ValueError('Missing worker command')
    folder = RUNTIME / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True); event_file = folder / 'events.jsonl'
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
    env[ENV] = str(event_file)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    session = {'title': title, 'state': 'running', 'started_at': time.time(), 'events': str(event_file),
               'log': str(folder / 'worker.log'), 'command': command}
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags)
    session['owner_pid'] = process.pid; save(folder / 'session.json', session)
    journal = Journal(event_file); view = View(title); screen = Screen(plain); lock = threading.Lock()
    def output_reader():
        with (folder / 'worker.log').open('wb') as log:
            for line in iter(process.stdout.readline, b''):
                log.write(line); log.flush()
                text = line.decode('utf8', errors='replace').rstrip()
                with lock: view.logs.append(clean(text)[:600])
                if not screen.live: print(clean(text), flush=True)
        process.stdout.close()
    reader = threading.Thread(target=output_reader, daemon=True); reader.start()
    interrupted = False
    try:
        while process.poll() is None:
            for event in journal.poll():
                with lock: view.apply(event)
                if not screen.live: print(f"[{event.get('phase','job').upper()}] {name(event.get('province',''))} {clean(event.get('message',''))}", flush=True)
            with lock: screen.draw(view)
            time.sleep(.3)
    except KeyboardInterrupt:
        interrupted = process.poll() is None
        if interrupted:
            cleanup=stop_worker(process)
            if cleanup:view.error=cleanup
    finally:
        reader.join(timeout=3)
        for event in journal.poll(): view.apply(event)
        screen.close()
    code = process.poll()
    view.state = 'interrupted' if interrupted else finish_state(view, code)
    view.waits.clear(); view.operation_wait = None
    emit('job', view.state, _file=event_file, message='本次进程已结束', error=view.error,
         counts=view.counts, output=view.output)
    session.update(state=view.state, exit_code=code, finished_at=time.time())
    save(folder / 'session.json', session)
    save(folder / 'result.json', {'state': view.state, 'counts': view.counts, 'regions': view.regions,
                                'model_ok': view.model_ok, 'model_failed': view.model_failed, 'cached': view.cached,
                                'error': view.error, 'output': view.output})
    print(view.render(min(110, shutil.get_terminal_size((100, 36)).columns), details=True))
    if view.output: print('RESULT PATH: ' + view.output)
    print('RUN LOG: ' + str(folder))
    return 130 if interrupted else (code or (1 if view.state in ('failed','incomplete','review_incomplete') else 0))


def published():
    view = View('PUBLISHED RESULTS'); view.state = 'complete'; view.phase = 'publish'; view.saved = True
    root = REPORTS / 'province-experiences'; latest = read_json(root / 'latest.json')
    batch = root / str(latest.get('id', 'absent')); data = read_json(batch / 'experiences.json')
    if not data.get('provinces'):
        view.state = 'incomplete'; view.message = '尚无已发布指南'; return view
    view.regions = {slug: p['state'] for slug, p in data['provinces'].items()}
    view.current = view.total = len(view.regions); view.output = str(batch)
    view.counts = latest.get('counts', {}); view.state = latest.get('state', 'complete_with_gaps')
    view.message = '已发布批次 ' + batch.name + ' / 新指南、历史记录与缺口分别列出'
    ai = latest.get('ai_reviewed', 0); pages = read_json(batch / 'openclaw-report-check/check.json')
    view.events.append(f"SOURCE AI {ai}/31   REPORT AI {pages.get('reviewed_pages',0)}/{pages.get('total_pages','--')}")
    view.events.append(f"REPORT FINDINGS {pages.get('issue_count','--')} / CONFIRMED {pages.get('confirmed_report_layout_issues','--')}")
    for path in batch.glob('*.docx'): view.events.append('WORD ' + path.name)
    catalog = read_json(ROOT / 'frontend/src/data/provinceCatalog.json')
    # Live capability data is a catalog snapshot, not an inferred AI verdict.
    entries = catalog.get('provinces', []) if isinstance(catalog, dict) else catalog
    if isinstance(entries, dict): entries = entries.values()
    if entries:
        apps = sum(bool(p.get('hasApplication')) for p in entries)
        evidence = sum(bool(p.get('hasEvidence')) for p in entries)
        view.events.append(f'DOCUMENTS 申请书 {apps} / 证据清单 {evidence} / 共 {apps+evidence} 类')
    return view


def saved_batch(folder):
    view = View('SAVED TASK / ' + folder.name); view.saved = True; view.output = str(folder)
    status = read_json(folder / 'status.json') or read_json(folder / 'session.json') or read_json(folder / 'check.json')
    if not status:
        view.state='incomplete';view.message='本目录没有可读取的任务状态';return view
    view.state=status.get('state',status.get('status','incomplete'));view.phase=status.get('phase','job')
    view.current=status.get('completed',status.get('reviewed_pages'));view.total=status.get('total',status.get('regions',status.get('total_pages')))
    view.counts=status.get('counts',{});view.error=status.get('error','');view.message='任务范围按本批次记录；不按目录时间推断全国完成'
    data=read_json(folder/'experiences.json').get('provinces') or read_json(folder/'results.json') or read_json(folder/'result.json').get('regions',{})
    if isinstance(data,dict):
        view.regions={slug:p.get('state','unknown') if isinstance(p,dict) else p for slug,p in data.items()}
    elif isinstance(data,list):
        view.regions={p.get('slug',p.get('province','')):p.get('state',p.get('status','observed')) for p in data}
    # A recovery may finish province files after a partial results.json was
    # written. The durable per-province task is the current source of truth.
    requested=status.get('requested_provinces',[])
    tasks={slug:read_json(folder/slug/'task.json') for slug in requested}
    for slug,task in tasks.items():
        if task.get('state'):view.regions[slug]=task['state']
    if tasks and all(tasks.values()):
        acquired=sum(bool(t.get('status',{}).get('guide_found')) for t in tasks.values())
        view.counts={**view.counts,'acquired':acquired,'gap':len(requested)-acquired}
    if view.total and len(view.regions)<view.total and view.regions:
        view.error='已读取 '+str(len(view.regions))+'/'+str(view.total)+' 个省份结果；缺失项不视为成功'
    if status.get('requested_provinces'):view.events.append('SCOPE '+str(len(status['requested_provinces']))+' 个省份（指定任务范围）')
    if status.get('derived_batch'):view.events.append('PUBLISHED '+status['derived_batch'])
    return view


def active_journal():
    from openclaw_task_service import worker_alive
    candidates = []
    for path in RUNTIME.glob('*/session.json'):
        data = read_json(path)
        if data.get('state') in ACTIVE:
            launch = {'owner_pid': data.get('owner_pid'), 'started_at': datetime.fromtimestamp(data.get('started_at',0)).astimezone().isoformat()}
            if worker_alive(launch): candidates.append((data.get('started_at',0), Path(data['events']), data.get('title','TASK')))
    for folder in (REPORTS / 'openclaw-tasks').glob('*'):
        status = read_json(folder / 'status.json'); launch = read_json(folder / 'launch.json')
        if status.get('state') in ACTIVE and worker_alive(launch) and (folder / 'progress.jsonl').exists():
            candidates.append((datetime.fromisoformat(launch['started_at']).timestamp(), folder / 'progress.jsonl', 'OPENCLAW / ' + folder.name))
    return max(candidates, default=None, key=lambda item: item[0])


def watch(plain=False, once=False, batch=None):
    saved = None
    batch_folder = None
    if batch:
        path = Path(batch).resolve()
        if not path.is_relative_to(ROOT): raise ValueError('Monitor path must be inside this project')
        saved = saved_batch(path if path.is_dir() else path.parent)
        batch_folder=path if path.is_dir() else None
        path = path / ('events.jsonl' if (path / 'events.jsonl').exists() else 'progress.jsonl') if path.is_dir() else path
        pointer=read_json(batch_folder/'terminal-progress.json') if batch_folder else {}
        if pointer.get('events'):
            actual=Path(pointer['events']).resolve()
            if not actual.is_relative_to(ROOT):raise ValueError('Job journal is outside this project')
            path=actual
        chosen = (time.time(), path, 'TASK MONITOR')
    else: chosen = active_journal()
    if once:
        view = saved or published()
        if batch and chosen and chosen[1].is_file():
            view = View(chosen[2])
            for event in Journal(chosen[1]).poll(): view.apply(event)
            view.saved = True
        print(view.render(min(110, shutil.get_terminal_size((100, 36)).columns), details=True))
        if view.output: print('RESULT PATH: ' + view.output)
        return 0
    screen = Screen(plain); current_path = None; journal = None; view = published(); last_plain = object()
    try:
        while True:
            if batch_folder:
                pointer=read_json(batch_folder/'terminal-progress.json')
                if pointer.get('events'):
                    actual=Path(pointer['events']).resolve()
                    if not actual.is_relative_to(ROOT):raise ValueError('Job journal is outside this project')
                    chosen=(time.time(),actual,'TASK MONITOR')
            selected = chosen if batch else active_journal()
            if batch_folder and not chosen[1].is_file():
                view=saved_batch(batch_folder)
            if selected and selected[1] != current_path:
                current_path = selected[1]; journal = Journal(current_path); view = saved or View(selected[2])
            if journal:
                for event in journal.poll():
                    view.apply(event)
                    if not screen.live: print(f"[{event.get('phase','job')}] {name(event.get('province',''))} {clean(event.get('message',''))}", flush=True)
            elif not selected: view.message = '暂无运行任务；显示已发布结果。等待新任务，Ctrl+C 返回。'
            screen.draw(view)
            if not screen.live and (current_path or 'idle') != last_plain:
                print(view.render(details=True)); last_plain = current_path or 'idle'
            time.sleep(1)
    except KeyboardInterrupt: pass
    finally: screen.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--title', default='COLLECTION / OPENCLAW')
    parser.add_argument('--plain', action='store_true'); parser.add_argument('--watch', action='store_true')
    parser.add_argument('--summary', action='store_true'); parser.add_argument('--batch', type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.watch or args.summary: return watch(args.plain, args.summary, args.batch)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    return run(command, args.title, args.plain)


if __name__ == '__main__': raise SystemExit(main())
