# Security Policy

## Reporting a vulnerability

**Do not open public issues for security vulnerabilities.**

Email **security@meridian.dev** with:

1. A description of the vulnerability
2. Steps to reproduce
3. Affected versions / branches
4. Any suggested mitigations

You can expect:

* Acknowledgement within **48 hours**
* A first triage update within **5 business days**
* A fix or mitigation plan within **30 days** for confirmed vulnerabilities

We follow [coordinated disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure):
we'll work with you on a public disclosure timeline once a fix is available.

## Supported versions

Until 1.0.0, only `main` is supported. Older branches are kept for history
but will not receive security backports.

## Hardening guidance for operators

If you run Meridian yourself, please:

* Set `ENVIRONMENT=production`. This forces fail-fast on missing
  `JWT_SECRET_KEY`, missing bootstrap users, and other dev shortcuts.
* Generate a strong JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
* Configure `CORS_ALLOWED_ORIGINS` explicitly. Wildcards are rejected.
* Replace the bootstrap admin/viewer env-var auth with a real IdP (OIDC/SAML).
* Rotate Neo4j and Postgres credentials away from defaults.
* Run behind an authenticated reverse proxy (nginx/Traefik/CloudFront) with
  TLS termination and a WAF.
* Subscribe to Dependabot alerts on the repo.

## Out of scope

* Vulnerabilities in dependencies — please report those upstream.
* Self-XSS that requires the user to paste arbitrary code into devtools.
* Best-practice issues that don't have a concrete impact (e.g. "your error
  page leaks the framework name").
