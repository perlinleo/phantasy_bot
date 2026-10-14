# Security Policy

## Supported versions

Security fixes are made against the latest development version. No historical release line is
currently supported.

## Reporting a vulnerability

Do **not** open a public issue for a vulnerability and never include a bot token, database,
Telegram user data, media artifact, or private URL in a report.

Use GitHub's private vulnerability reporting / Security Advisories for this repository. If that
feature is not enabled, contact a maintainer through their GitHub profile and request a private
reporting channel. Include the affected commit/version, impact, minimal reproduction, and a safe
proof of concept.

We aim to acknowledge reports within 7 days. Fix timing depends on severity and reproducibility;
please do not disclose details publicly until a fix or mitigation has been agreed.

## Scope

Important areas include token handling, ACL bypass, callback/job ownership, SQLite concurrency,
path traversal, subprocess arguments, Blender/FFmpeg execution, Telegram delivery, and generated
media that might disclose private input.
