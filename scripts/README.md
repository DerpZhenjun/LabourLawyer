# Client checks and build receipts

Run the pipeline from the repository root with Node.js 22.18+ (or a newer supported Node.js release) and the already installed dependencies of each selected client. Shared contract tests import TypeScript directly. Use the repository's existing Python virtual environment when generating/checking the backend API contract; see the API generator's documentation for its Python selection options.

```sh
node scripts/client-pipeline.mjs plan --targets web,mini,android,desktop
node scripts/client-pipeline.mjs check --targets web,mini
node scripts/client-pipeline.mjs build --targets web,mini
node scripts/client-pipeline.mjs build --targets android
node scripts/client-pipeline.mjs build --targets desktop
node scripts/client-pipeline.mjs build --targets avatar
node --test scripts/test-client-pipeline.mjs
```

`--targets` is a comma-separated list. The default list is `web,mini,android,desktop`; the ChatVRM avatar is opt-in. Steps execute sequentially in a stable dependency order. A nonzero or missing process exit status stops the run, and later steps are marked `blocked`. `android:check` checks its shared frontend and contracts; an actual APK build is required to verify the Android toolchain. `desktop:check` also runs the desktop server tests.

`plan` plans a build. `check --dry-run` and `build --dry-run` plan the respective operation. These modes execute zero subprocesses and only write a `planned` receipt. They do not check installed SDKs, validate output files, or provide evidence that a build passed.

| Target | Existing commands used | Output captured after a build |
| --- | --- | --- |
| Shared | `sync-client-release.mjs --check`, stable API/regional/client generated-output checks and shared AI/regional contract tests | Release metadata and contract/source fingerprint in receipt |
| `web` | `frontend` typecheck and build | Every file under `frontend/dist` |
| `mini` | `miniprogram` test and build, including existing prebuild drift checks | Deployable JS/JSON/WXML/WXSS/assets, excluding compiler, tests, scripts, TypeScript source and private/project configuration |
| `android` | `mobile` android:apk, which includes Capacitor sync and frontend build | `frontend/dist` and `mobile/android/app/build/outputs/apk/debug/app-debug.apk` |
| `desktop` | `desktop` test and dist | The current package version's x64 Windows setup and portable executables under `.runtime/releases/<version>/desktop/artifacts` |
| `avatar` | Local ChatVRM TypeScript compiler and existing build | `.next` output excluding cache and trace files |

Shared graph dependencies run once. The release metadata check validates the single `config/client-release.json` manifest against client metadata and generated mini release information before client checks run. The release synchronization script and executed shared contract/API test scripts are fingerprinted, so editing a verification body after a build invalidates its evidence. When selecting web and Android together, Android's existing APK script supplies the frontend build; the web build step records that dependency. Frontend build still executes its explicit `vue-tsc --noEmit` and Vite commands. For frontend/APK builds only, `npm --ignore-scripts` suppresses redundant lifecycle contract generation because the pipeline already checked generated contracts. Mini-program lifecycle drift checks remain enabled. Desktop's helper builds its own frontend using its release-specific environment and directory.

The mini build validates checked-in generated JavaScript and data modules with the existing npm lifecycle and tests. It can therefore attest existing source modules without requiring new timestamps. Regenerate intentionally changed mini sources first using the existing `npm --prefix miniprogram run compile`, then rerun the checks. The pipeline does not repair contract drift automatically.

## Receipts and artifact allowlists

Each run writes `.runtime/client-pipeline/<unique-run>/receipt.json`. It records the exact commands, relative working directories, dependency plan, timestamps, actual exit codes, step statuses, selected input fingerprint, and output paths, sizes and SHA-256 checksums. Interrupted/running, failed, check-only, and planned receipts cannot prepare release artifacts. Paths in receipts are repository-relative. Receipts are local verification records; they are not signed release attestations.

Prepare a file allowlist from a successful build:

```sh
node scripts/client-pipeline.mjs artifact --receipt .runtime/client-pipeline/<run>/receipt.json
```

This writes `artifact-allowlist.json` beside the receipt. It does not copy files or publish. The stage requires an unchanged pipeline plan, every expected successful step and exit code, an identical current input fingerprint, and the same complete output paths, sizes and checksums. It rejects missing/empty/modified outputs, receipts older than 24 hours, path traversal, and artifact symlinks/junctions. Excluded dependency directories such as `node_modules` are not walked. Input fingerprints cover the selected clients, shared packages, backend sources, configuration and public regional source data. Private `backend/data` and `backend/uploads` folders are excluded entirely; public release seeds remain included through `data/public-regions`. Database files (`.db`, `.sqlite`, `.sqlite3`, including WAL/SHM/journal companions), local environment and generated build/cache files are excluded from snapshots. Database files and the private backend runtime folders are also excluded from artifact allowlists.

Vite preserves timestamps when copying files from `frontend/public`. For the frontend output, an old timestamp is accepted only when the output matches the exact relative file under that declared static source root, including size and SHA-256, and the source is part of the verified current input snapshot. The receipt records `staticCopy: true` and the repository-relative `sourcePath`; artifact preparation independently verifies that mapping again. This applies to standalone web and Android's embedded frontend build, and does not change file timestamps.

Other pre-existing old generated output requires a prior verified successful build receipt proving that the same paths and exact bytes belong to identical current inputs. This prevents a command that exits successfully without producing output from attesting an unrelated old APK or compiled JavaScript. To reuse an incremental Gradle or other build safely:

```sh
node scripts/client-pipeline.mjs build --targets android --reuse-receipt .runtime/client-pipeline/<prior-run>/receipt.json
```

The prior receipt must still pass verification before commands start, including its complete current artifact checksums, source fingerprint and 24-hour lifetime. Unchanged old files are explicitly marked `reused: true` with a `reusedFrom` receipt link. A package version or input change invalidates that route. Reuse chains are verified at the artifact stage; preserve the referenced receipts. Without a compatible prior receipt, regenerate the output with the existing build tooling. A dry-run cannot become a reuse receipt.

## Build prerequisites and existing helpers

Configure dependencies explicitly before running the pipeline; it never runs npm install. The APK target delegates to the existing `mobile` `android:apk` script. Its current `gradlew.bat` command requires Windows, a compatible installed JDK (the project uses JDK 21), Android SDK and accepted local licenses, and a configured Gradle cache/network. Set `JAVA_HOME`, Android SDK variables and `GRADLE_USER_HOME` in the invoking environment as appropriate. The orchestrator preserves that environment and does not guess installations or modify global temporary directories. The existing `scripts/install-mobile.ps1` contains the project's device installation flow and JDK/cache setup, but also installs dependencies, configures adb and changes the device; the pipeline never invokes it. Device installation is a separate explicitly requested operation.

The current desktop helper produces Windows x64 installers and requires its installed Electron/build dependencies and locally available packaging tools. ChatVRM is optional, uses its own older dependency stack and can require environment-specific maintenance; it is not started by this command. A failed optional build remains a failed receipt.

`start.bat` and the existing scripts under `scripts/launcher` remain the development launch entry points. Build/check/artifact commands do not start models or services, stop/restart existing processes, install APKs, upload to WeChat/app stores/cloud hosting, or read GitHub credentials. A prepared allowlist proves only the recorded local checks and build outputs; signing, store review and publication require their own evidence.
