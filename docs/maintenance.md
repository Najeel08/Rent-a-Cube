# Maintenance notes

## Booking and account rules

- Booking times use `Asia/Kolkata`. Prices are whole INR per hour; provider
  amounts are converted to paise on the server. Duration is 1–72 hours.
- A workspace is reserved for one booking at a time. Capacity is descriptive;
  the application does not sell individual seats. Adjacent bookings are allowed.
- A cart does not reserve inventory. Checkout holds last 15 minutes.
- Payments must match the stored order, amount and currency and be captured.
  A valid signature alone does not mark a booking as paid.
- An uncertain refund is kept for review rather than automatically retried.
- Owner approval is checked on owner and technician requests. Password changes
  invalidate old portal sessions. Technician setup links expire after one hour.
- The legacy `TechnicianCredential` model is retained for existing databases;
  the technician portal uses the `Technician` model in `owners`.

## Existing databases

Keep all migration files. Historical app labels, table names and column names
remain for compatibility even where the Python model names have changed.

1. Stop application writes and back up the database, `media/` and `private_media/`
   together. Use SQLite's backup API if the database is still open.
2. Run `python tools/preflight_db.py PATH_TO_DATABASE` with the project environment.
   It reports aggregate integrity checks without changing data.
3. Test migrations on a restored copy with separate media directories, then
   apply `python manage.py migrate` to the intended database and restart workers.
4. If rollback is needed, restore the matching code, database and media snapshot.
   Reconcile any payment activity since the backup before reopening.

Use `DJANGO_DB_PATH`, `DJANGO_MEDIA_ROOT` and `DJANGO_PRIVATE_MEDIA_ROOT` to isolate
copies. `DJANGO_LOAD_ENV=0` disables loading the local `.env`.

The existing local data has four paid bookings without complete slot information
and five chat messages without verified participant links. These records are
preserved. Confirm their original details before editing them; do not guess.
Unlinked paid bookings conservatively block that owner's inventory.

For payment recovery, `python manage.py reconcile_payments BOOKING_ID` reads the
provider and records a matching capture or completed refund. It does not charge
or issue refunds. An uncertain refund without a provider ID needs manual review.

## Before public deployment

Use a production server, HTTPS, a strong stable secret and explicit allowed hosts.
Run `python manage.py check --deploy` with the actual production environment.
Local HTTP/debug settings are not production settings. Keep private proofs outside
the public web root; protect backups and redact setup links from access logs.
Configure SMTP and test payment capture, interrupted callbacks and refunds in the
provider sandbox. Schedule expired-session cleanup with `manage.py clearsessions`.

Login limits use the connection's `REMOTE_ADDR`. A trusted proxy must supply the
real client address; arbitrary forwarded headers are not accepted. SQLite uses
IMMEDIATE transactions to serialize booking writes; its throughput needs testing
before serving many concurrent users. There is no background payment worker,
public webhook, MFA or customer/owner self-service password recovery.

## Third-party assets

The interface includes Bootstrap, Font Awesome and existing template assets.
Retain their copyright/license notices. The repository does not establish a new
license for third-party images or templates; verify their redistribution terms
before publishing. Do not upload real customer data, identity proofs or credentials.
