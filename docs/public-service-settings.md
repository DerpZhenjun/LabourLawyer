# Persistent digital service address

The Windows web launcher and scoped backend restarter load the public address from `.runtime/service-origins.json`, before starting the API. This file contains no credentials and is local to the installation:

```json
{"digital":"http://YOUR_PRIVATE_LAN_IP:8089"}
```

An explicit process environment variable `LABOURLAWYER_DIGITAL_URL` takes precedence. The loader reuses the backend origin validator, rejects credentials, paths, query strings, fragments and invalid ports, and permits HTTP only for loopback/private IP addresses. Public hosts require HTTPS. It neither probes the address nor starts a model or remote process.

When an address is configured, `start-web.ps1` skips starting a Windows digital webpage and uses the existing remote digital service. The API exposes its validated public address through `GET /api/services`; web and packaged clients discover it from their selected API. An explicit saved client digital address remains the user's override. An unavailable service is reported as unavailable, without silently selecting another computer's localhost.

Keep the address unset for the existing local digital development workflow. Restart the project's API normally after changing server configuration; an already running process does not inherit new environment variables. Do not change a user's selected API or case database as part of this operation.

Validation: `powershell.exe -NoProfile -File scripts/test-public-service-settings.ps1` exercises absence, persistence, environment precedence and invalid address/configuration cases without contacting any service.
