# Security Notes

## Current Security Model

GiuMan Assistant is currently designed for local or trusted-network usage only.

The system is NOT hardened for public internet exposure.

## Assumptions

- The assistant runs on a trusted machine or local network.
- Secrets are stored locally in `.env`.
- `.env` must never be committed to Git.
- `db/`, `raw/`, and local indexes are considered local-only data.

## Current Risks

### URL ingestion
External webpages may contain:
- prompt injection
- malicious instructions
- misleading content

External content should be treated as untrusted.

### Local file writes
LLM-generated content must not arbitrarily overwrite files without validation.

### Network exposure
The Streamlit application should not be directly exposed to the public internet without:
- authentication
- HTTPS
- reverse proxy
- rate limiting

## Recommended Future Hardening

- Safe path validation
- URL validation and filtering
- File write sandboxing
- Authentication layer
- HTTPS via reverse proxy
- Trusted/untrusted content separation
- Audit logging

## Operational Guidance

Recommended deployment:
- local machine
- Raspberry Pi on trusted LAN
- VPN-protected network

Avoid:
- public exposure
- direct port forwarding
- disabling SSL verification