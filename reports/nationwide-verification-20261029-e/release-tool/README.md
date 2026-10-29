# E4 release tool verification

The tool tests pass. This report does not claim that E4 has been appended, accepted in the candidate UI, prepared against live data, or published.

`backend/candidate_review.py` adds `E_FILES`, `load_e_guides(root)`, the 21-source verifier branch, and `append_e(root, output)`. The loader uses each E provider's canonical parser and forwards the explicit root through capability checks. Mutable raw guide flags cannot authorize generation. Candidate append requires the existing 17 / 198 / 181 baseline and appends four exact scopes as versions 199–202, producing 21 / 202 / 185. It preserves the earlier manifest, consistent backups of both SQLite stores, and exact guide-store bytes under `before-e-extension`. It checks scope, source history, sequence, hashes, and manifest again under the write lock. Failure restores exact guide-store and manifest bytes without writing the directory database or replacing an external manifest update.

`backend/reviewed_oct29e_release.py` provides `prepare(root, output)`, `verify_prepared(root, output)`, `verify_receipts(root, guides)`, and `apply(root, output)`. Preparation requires all eight genuine native UI document records: application and evidence for 相城 320507, 吴江 320509, 富阳 330111, 建德 330182. Every record must bind its candidate source/version/template, HTTP 200, `native_ui_generation=true`, `api_replay_used=false`, own source response header, and `official-blank-filled` origin. Actual DOCX ZIP integrity and Word document/body XML are checked. Every visual page must have a unique contained PNG path, matching SHA, valid chunk CRCs, decodable pixels, and a PASS visual record. Missing one document or page prevents preparation.

Main apply accepts only `http://127.0.0.1:8000/api/regional-guides/release-capabilities` with `oct29e-own-localities-v1`, `main_default`, the two E adapters, source binding, and no model requirement. It requires main 198 current / 206 history, 4,294 discovery jobs, and queue 28. It appends main versions 207–210 and produces public 202 / 185, history 210, queue 24. Existing facts, source history, directory bytes, job records, and remaining queue metadata are preserved. Post-commit failure restores exact standalone main SQLite bytes. The tool never starts, stops, restarts, or discovers processes or models.

Only exact platform lifecycle notices are removed in the publication projection. Official source warnings and `source_issues` remain. Source, capability, public proof, and exporter calls use the explicit selected root; the export script is loaded from that root's `scripts/export-public-data.py`.

Verification commands:

```powershell
$env:PYTHONPATH='backend'
python -m unittest backend.tests.test_reviewed_oct29e_release -v
python -m unittest backend.tests.test_reviewed_oct29c_release backend.tests.test_reviewed_oct29d_release -v
```

E: 26 tests passed in 82.413 seconds. C/D: 32 tests passed in 104.606 seconds. Every release execution in these tests used synthetic files and temporary SQLite fixtures. Canonical provider and proof boundaries are controlled test doubles that assert root forwarding; this suite does not stand in for E provider attachment, Word, browser, or independent public-root integration acceptance. The full integration suite remains a separate gate after the shared dispatch and provider integration is complete.

TDD evidence: the initial 20 tests failed because the E module was absent. Three additional behavior tests then failed for missing response-header enforcement, a lock-time manifest update, and inexact post-commit SQLite restoration. A further explicit-root exporter test failed because the reused helper read the original checkout's script. All these failures were reproduced before their fixes. Complete diagnostic traces remain private; the public test log contains only test names and results.
