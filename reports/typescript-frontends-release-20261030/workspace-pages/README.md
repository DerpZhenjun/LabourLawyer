# Typed administration and workspace pages

PASS for the six administration views (Dashboard, CaseCenter, DeadlineCenter, DocumentCenter, EvidenceCenter and KnowledgeCenter), DocumentWorkspace and DistrictWorkflow. Actual scripts and templates compile under strict TypeScript, unchecked-index checks, exact optional properties and strict Vue templates. Ten genuine type counterexamples are rejected at their expected source lines. Twelve isolated runtime/mounted regressions pass, along with separate malformed-storage and denied-storage-getter checks.

```text
node scripts/test-workspace-page-types.mjs
node scripts/test-workspace-page-types.mjs --baseline-storage
node scripts/test-workspace-page-types.mjs --storage-getter-denied
```

The existing baseline project configuration passed before migration; it included only the earlier narrow SFC set. This report's dedicated temporary configuration explicitly includes all eight owned SFCs and their actual imports. It does not modify project configuration or disable checking. `--runtime-only` is available for investigating runtime behavior while another imported component is under migration; that mode explicitly records SFC compilation as NOT_RUN.

The new pure workspace module provides case/input/storage types and validators for unknown saved JSON, existing portal-report/task lists and district workflows. The Vue composable retains a JavaScript re-export. Existing example cases, template links, search, stage filtering, creation/cancel and explicit report/collection/download controls remain. No backend case service is introduced. Report/task GET bodies enter as unknown; displayed values are checked before iteration. In-flight report responses cannot restart polling after unmount, and old district responses cannot replace a newly selected locality.

Local storage is read without writing. Valid saved cases retain unrelated top-level and per-case metadata. Unsupported or unreadable saved content remains untouched; examples are displayed with a notice in every case-consuming page. Further edits in that session stay in memory and cannot overwrite the protected saved bytes. Failed writes also retain the current in-memory case and show a notice. Invalid numeric input is rejected before it can reach numeric rendering or persistence. Empty saved case arrays retain the earlier example fallback behavior.

The first real RED exposed a saved string amount reaching numeric rendering. Additional REDs exposed missing example-fallback notices after malformed JSON, on the dashboard consumer, and after a denied global storage getter. Their GREEN checks preserve the saved bytes. `RED.json` describes these observations; complete diagnostic traces remain private.

Mounted checks compile the real SFC scripts and templates and run Vue's custom renderer against an in-memory host. Storage, router, transport, downloads and asynchronous task responses are isolated synthetic fixtures. Valid portal rows, existing resume/province/vision request payloads and file-download calls are exercised without contacting a server, starting a collection task or calling a model. DOM host behavior needed by Vue directives is represented in the harness; this does not claim browser layout, pointer behavior or native downloads.

No owned implementation blocker remains. Actual Chrome responsive and interaction acceptance, Android packaging/signing/device acceptance, broad integration checks and publication are separate release gates. They were not performed by this scoped work. Backend, official sources, databases, services, shared index/CJS pins and Git were not changed by this work. `PUBLIC-WHITELIST.json` lists the exact source and public report files and excludes itself.
