# Independent signed Android preview

The original debug app remains `cn.labourlawyer.mobile`, with its existing Android debug certificate and data. The release variant is a separate app, `cn.labourlawyer.mobile.release`, labelled **LabourLawyer 独立签名预览**. It requires a fresh side-by-side installation and does not replace or migrate the old app. This signing workflow does not install an APK or publish to a store.

The release variant disables Android debugging and uses a generated, release-only Capacitor configuration that disables WebView debugging. The debug configuration and base package remain unchanged. See [Android build variants](https://developer.android.com/build/build-variants) and [Android app signing](https://developer.android.com/studio/publish/app-signing).

## Permanent identity and backup

The default permanent directory is `$USERPROFILE/.labourlawyer/signing`, outside every checkout. It contains:

- `release-preview.p12`: encrypted PKCS12 with the persistent RSA3072 application key.
- `release-preview.password.dpapi`: its CSPRNG password encrypted with Windows DPAPI CurrentUser. The password is not a command-line argument or a repository property.
- `release-preview.cer` and `release-preview.identity.json`: public certificate and identity/hash metadata.
- `backup-initial/`: verified copies of the original encrypted key, DPAPI credential and identity metadata.

Only the current Windows user SID and SYSTEM receive full access. Ownership is checked; the helper does not take over another owner's signing files. Existing complete identity files are verified and reused. Partial identities, hash changes and backup inconsistencies stop rather than generating a replacement key. The certificate SHA256 must remain the same for subsequent updates of the independent package.

DPAPI recovery depends on the original Windows user/profile protection. The initial local backup protects against file corruption but is not an off-machine disaster-recovery backup. Keep a separately protected owner-controlled copy and an independently retained password for a portable export. Never create a new signing key merely because the old password/profile is unavailable.

Owner-initiated portable export uses an NTFS private destination outside the checkout and a SecureString password entered by the owner:

Run the export inside the same PowerShell session so the SecureString is passed as an object rather than placed on an operating-system command line:

```powershell
$ownerBackupPassword = Read-Host 'Portable backup password (at least16characters; retain separately)' -AsSecureString
& ./scripts/build-signed-android.ps1 `
  -ExportBackupDirectory "$env:USERPROFILE/.labourlawyer/owner-backup-NEW" `
  -BackupPassword $ownerBackupPassword
```

The exported PKCS12 is encrypted with the owner-supplied password while retaining the original certificate/key. Its file bytes/hash differ because it is re-encrypted. Verify the certificate SHA256 and alias before any owner-controlled restore. The automatic helper will not silently adopt a changed keystore or identity. No key or plaintext password is uploaded to GitHub, Ubuntu or a store.

## Build after reviewed web synchronization

First synchronize the reviewed web build through the normal project pipeline. This helper deliberately does not rebuild or synchronize web sources and never invokes a device installer:

```powershell
pwsh -NoProfile -File scripts/build-signed-android.ps1 -PrepareKeyOnly
pwsh -NoProfile -File scripts/build-signed-android.ps1
```

It uses the explicitly configured JDK21/Android SDK and D-drive Gradle/temp directories with process-scoped environment variables. Gradle has one worker, a512MiB heap, no persistent daemon, no configuration/build cache, and Kotlin compilation is requested in-process. Environment values are restored afterwards. Signing passwords reach keytool/Gradle through environment variables; the JDK's `-storepass:env`/`-keypass:env` options keep them out of process arguments. Raw tool logs remain under ignored `.runtime`.

The helper verifies APK signature/certificate and package ID, checks Android/WebView debugging are disabled, compares every packaged web file to the synchronized input, checks signing material/password are absent from the APK, and records an APK SHA256. It produces an APK and validation receipt in a new `.runtime/signed-android/` directory; existing evidence is never overwritten. It does not create a pipeline release attestation or publish anything. Root-owned release verification must associate the final synchronized input and signed APK with the final frozen source revision.

## This validation

The first signed validation is native version `1.2.0-preview.4`, code7, using87older synchronized web files copied into the isolated worktree from the earlier reviewed debug build. It is **validation only**, and must not be published as the final updated client. The final overnight build must synchronize the frozen current frontend first and reuse this permanent certificate.

The signed APK passed `apksigner verify`, uses APK Signature Scheme v2, has a distinct certificate and package, is not debuggable, and contains the release-only configuration. The original main-workspace debug APK retains its exact bytes and original certificate. No Android device was connected and no installation/runtime device acceptance was performed. Signing does not imply Play/App Store publication, publicly trusted Windows Authenticode, or successful device installation.
