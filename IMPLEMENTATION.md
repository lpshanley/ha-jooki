# Implementation record

## Layout

- One Home Assistant integration package: `custom_components/jooki`.
- Platform modules at the package root are the inbound handlers. Home Assistant requires those filenames.
- `JookiDevice` in `device_commands.py` is the public operation surface stored on `entry.runtime_data`.
- `JookiMqttClient` is the MQTT accessor. Composition in `__init__.py` constructs it. There is no DAO.
- No role-named directories.

## Required check

`pytest` in `.venv`, including the platform import check.

## Standard revisions reviewed on 2026-10-27

- BACKEND.md living standard, revision 2026-10-11
- backend/boundaries.md living standard, revision 2026-10-16
- backend/language-conventions.md living standard, revision 2026-10-16
- SYSTEM.md proposed draft, revision 2026-10-11
- backend/service-bootstrap.md proposed draft, revision 2026-10-11
