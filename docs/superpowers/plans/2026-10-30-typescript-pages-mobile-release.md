# TypeScript pages and Android release implementation plan

Goal: Continue the approved gradual TypeScript migration across remaining Vue pages, preserve existing behavior and precise locality contracts, then build and publish an updated Android preview.

Architecture: Reuse verified regional contracts. Add explicit types at untrusted JSON/storage/stream boundaries; retain JavaScript compatibility imports for existing consumers and tests. Separate public regional pages, administrative workspace pages, and provincial document forms to allow independent implementation. Root integrates shared AI/network contracts, application shell, strict compilation, actual browser checks, Android packaging and GitHub release.

Constraints: Preserve six user-modified files, official sources/templates and 202/185 coverage; no Windows model startup, model inference, account changes, guide publication or database rebuilding. No blanket any, ts-ignore, or check disabling as a migration substitute. No add-all Git. No attribution to the assistant. New release must identify actual client/backend dependencies and test limits.

- [ ] Record current source and protected file hashes; inspect existing build/install/release tooling.
- [ ] Independently migrate public regional views and presentation/data dependencies with strict component checks and behavior regressions.
- [ ] Independently migrate administration/workspace views and typed stored data without discarding invalid saved data.
- [ ] Independently migrate historical provincial document forms, specific field components and document request boundaries; preserve 34 client payloads.
- [ ] Migrate app shell and AI-facing components; centralize portable AI request/response/stream handling for web and mini with runtime tests.
- [ ] Enable strict Vue checks for migrated pages, retain unmigrated JavaScript compatibility explicitly, and verify existing source/contract invariants.
- [ ] Run type/build, relevant and full regression suites, actual Chrome responsive/interaction/download checks, and native client checks where available.
- [ ] Build versioned Android APK, verify signature/manifest/embedded assets/SHA, and update connected authorized phone if available without uninstalling.
- [ ] Commit tested source in exact batches, publish a new GitHub prerelease with actual APK/checksums/instructions, and verify remote download bytes.
- [ ] Save release and acceptance evidence, truthful limitations and a resume checkpoint.
