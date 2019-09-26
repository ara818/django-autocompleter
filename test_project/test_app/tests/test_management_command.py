from django.core.management import call_command
from django.test import TestCase


class ManagementCommandTestCase(TestCase):

    def test_autocompleter_init_calleable(self):
        """
        Can call autocompleter_init without any error
        """
        try:
            call_command("autocompleter_init")
        except Exception:
            self.fail("Calling autocompleter_init has raised an exception unexpectedly")
