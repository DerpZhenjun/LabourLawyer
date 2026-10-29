# Shared regional contract parity

Final result: **PASS** for all 23 actual adapter/document-kind profiles. The real Python validator and both shared TypeScript and generated mini-program runtimes agree on all 8,253 JSON-transportable vectors. A further 202 local shape vectors pass in both JavaScript runtimes, for 16,910 JavaScript validation comparisons in total.

Run from the repository root with a Node runtime supporting native TypeScript type stripping and the existing Python environment:

```text
node scripts/test-regional-contract-parity.mjs --fresh-source-contracts
```

This fresh-source mode reads the public source inventory, selects each distinct adapter/kind, and calls the real `build_form_contract` with an explicit repository root. Own-template and public-source checks execute normally. Versions are synthetic sequence values used only by this fixture. No SQLite store, live API, browser, model, service, or document renderer is used.

Without this flag the script uses the complete context-bearing fixture at `.runtime/typescript-full-contracts.json` when present; otherwise it builds fresh contracts in memory. `--contracts`, `--python`, and `--report-dir` permit explicit alternative locations. Field names, capacities, choices, copy rules and layout tables come from the actual contracts; the script does not maintain a second locality field catalogue.

Coverage includes every profile's empty defaults and fictional example; Unicode codepoint capacity; valid and invalid calendar dates; declared choices; unknown empty and nested fields; XML-invalid characters and lone surrogates; copy strings, leading zeros, numeric values and nullability; list capacities and aggregate request text; and Feidong line widths, East Asian Width ranges, newlines, trimming, unassigned codepoints, emoji and combining characters. Symbols, inherited records, null-prototype records, sparse arrays and arrays with extra properties are explicitly local JavaScript tests because JSON cannot preserve these shapes.

For accepted data, both request builders must preserve all raw values and the exact source/version/template/kind/mode context. Python may perform its documented integer-copy normalization; all other Python values must remain unchanged. Technical capacities are not represented as official filing requirements.

`RED.json` preserves the first failing run: two evidence profiles returned entirely blank examples because their original/copy choice contained unsupported example text; Feidong trimming disagreed on U+0085 and U+FEFF in 48 comparisons. The shared runtime owner corrected these two behaviors and regenerated the mini-program runtime. The final fresh-source run in `RESULT.json` has no differences and pins the tested source, generated runtime, fixture bytes and script with SHA-256. The initial run had fewer vectors while coverage was still being extended.

These are pure contract/runtime results. They do not claim browser acceptance, document layout review, live publication, or verification of live source version numbers. The exact public file list is in `PUBLIC-WHITELIST.json`; the whitelist excludes itself.
