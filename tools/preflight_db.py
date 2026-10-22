"""Read-only SQLite checks before upgrading an existing Rent-a-Cube database.

Usage: python tools/preflight_db.py /path/to/database.sqlite3
Only aggregate counts are emitted; no personal data or credential values.
"""
import argparse
import sqlite3
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    args = parser.parse_args()
    path = args.database.resolve(strict=True)
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    failures = 0
    try:
        integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
        foreign_keys = len(connection.execute('PRAGMA foreign_key_check').fetchall())
        print(f'integrity_ok={integrity == "ok"}; foreign_key_errors={foreign_keys}')
        failures += int(integrity != 'ok') + foreign_keys
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, column in [('user_user_tb', 'Email'), ('owners_owner_tb', 'Email'),
                              ('owners_addtech', 'Email'), ('technician_tech', 'Email'),
                              ('workadmin_projectadmin', 'email')]:
            if table not in tables:
                continue
            # Identifiers below are a fixed allowlist, never user input.
            count = connection.execute(f'SELECT COUNT(*) FROM (SELECT LOWER("{column}") FROM "{table}" GROUP BY LOWER("{column}") HAVING COUNT(*) > 1)').fetchone()[0]
            print(f'{table}: duplicate_email_groups={count}')
            failures += count
        if 'user_cart' in tables:
            checks = {
                'invalid_money_or_duration': '"Price" <= 0 OR "nohrs" NOT BETWEEN 1 AND 72 OR "totalsum" < 0',
                'invalid_payment_state': '("Refundstatus" = 1 OR "Status" = 1) AND "Paystatus" = 0',
            }
            for name, condition in checks.items():
                count = connection.execute(f'SELECT COUNT(*) FROM user_cart WHERE {condition}').fetchone()[0]
                print(f'bookings: {name}={count}')
                failures += count
            for column in ['RazorpayOrderId', 'RazorpayPaymentId']:
                count = connection.execute(f'SELECT COUNT(*) FROM (SELECT "{column}" FROM user_cart WHERE "{column}" != \'\' GROUP BY "{column}" HAVING COUNT(*) > 1)').fetchone()[0]
                print(f'bookings: duplicate_{column}_groups={count}')
                failures += count
            columns = {row[1] for row in connection.execute('PRAGMA table_info(user_cart)')}
            if {'workspace_id', 'StartTime'} <= columns:
                count = connection.execute('SELECT COUNT(*) FROM user_cart WHERE "Paystatus" = 1 AND (workspace_id IS NULL OR "StartTime" IS NULL)').fetchone()[0]
                print(f'warning: paid_legacy_bookings_needing_slot_review={count}')
        if 'owners_workassign' in tables:
            count = connection.execute('SELECT COUNT(*) FROM (SELECT request_id FROM owners_workassign WHERE request_id IS NOT NULL GROUP BY request_id HAVING COUNT(*) > 1)').fetchone()[0]
            print(f'assignments: duplicate_request_groups={count}')
            failures += count
    finally:
        connection.close()
    if failures:
        print('STOP: resolve conflicting data with an operator before migration. No rows were changed.')
    else:
        print('Preflight passed. Back up database AND media before migration; this is not a backup.')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
