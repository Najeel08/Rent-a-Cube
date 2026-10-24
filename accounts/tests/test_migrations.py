"""Migrations tests and fixtures."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.urls import reverse
from home.models import AbuseWindow


class AbuseWindowMigrationTests(TransactionTestCase):
    def test_unapplied_migration_blocks_login_and_migration_restores_it(self):
        """Reproduce the exact missing table, only inside Django's test database."""
        self.assertIn('homeapp_abusewindow', connection.introspection.table_names())
        try:
            MigrationExecutor(connection).migrate([('homeapp', '0001_supportinquiry')])
            self.assertNotIn('homeapp_abusewindow', connection.introspection.table_names())
            for role in ['technician', 'admin']:
                with self.assertLogs('config.middleware', level='ERROR'):
                    response = self.client.post(reverse(role + '_login'), {'email': 'unknown@example.test', 'password': 'wrong'})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('role', self.client.session)
        finally:
            MigrationExecutor(connection).migrate([('homeapp', '0002_abusewindow')])
        self.assertIn('homeapp_abusewindow', connection.introspection.table_names())
        for role in ['technician', 'admin']:
            response = self.client.post(reverse(role + '_login'), {'email': 'unknown@example.test', 'password': 'wrong'})
            self.assertEqual(response.status_code, 200)
        self.assertGreater(AbuseWindow.objects.count(), 0)
