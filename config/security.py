"""Keep password-setup bearer links out of application logs and email previews."""
from copy import copy
import logging
import re

from django.core.mail.backends.console import EmailBackend
from django.utils.log import ServerFormatter


SETUP_LINK = re.compile(r'(/technicians/activate/)[^/\s?\"\'<>]+')


def redact_setup_links(text):
    return SETUP_LINK.sub(r'\1[redacted]', text)


class SetupLinkFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact_setup_links(record.getMessage())
        record.args = ()
        return True


class SafeFormatter(logging.Formatter):
    def format(self, record):
        return redact_setup_links(super().format(record))


class SafeServerFormatter(ServerFormatter):
    def format(self, record):
        return redact_setup_links(super().format(record))


class RedactedConsoleEmailBackend(EmailBackend):
    """Preview email locally without printing a usable password-setup token."""

    def write_message(self, message):
        preview = copy(message)
        preview.body = redact_setup_links(message.body)
        super().write_message(preview)
