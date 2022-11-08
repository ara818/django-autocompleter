from optparse import make_option
import logging

from django.core.management.base import BaseCommand

from autocompleter import Autocompleter


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            action="store",
            dest="name",
            help="Name of autocompleter to initialize. Defaults to default autocompleter name.",
            type=str,
        )
        parser.add_argument(
            "--remove",
            action="store_true",
            default=False,
            dest="remove",
            help="Remove all autocompleter data. Default to false.",
        )
        parser.add_argument(
            "--store",
            action="store_true",
            default=False,
            dest="store",
            help="Store all autocompleter data. Default to false.",
        )
        parser.add_argument(
            "--clear_cache",
            action="store_true",
            default=False,
            dest="clear_cache",
            help="Clear cache for autocompleter. Default to false.",
        )
        parser.add_argument(
            "--skip_delete_old",
            action="store_false",
            default=True,
            dest="delete_old",
            help="Do not clear old terms from autocompleter when storing. "
            "Recommended only to be used with store all after remove_all otherwise orphan keys will remain.",
        )

    help = "Store and/or remove autocompleter data"

    def handle(self, *args, **options):
        # Configure logging
        level = {0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}[
            options.get("verbosity", 0)
        ]
        logging.basicConfig(level=level, format="%(name)s: %(levelname)s: %(message)s")
        self.log = logging.getLogger("commands.autocompleter_init")

        autocomp = Autocompleter(options["name"])
        if options["remove"]:
            self.log.info(
                "Removing all objects for autocompleter: %s" % (options["name"])
            )
            autocomp.remove_all()
        if options["store"]:
            delete_old = options["delete_old"]
            self.log.info(
                "Storing all objects for autocompleter: %s" % (options["name"])
            )
            autocomp.store_all(delete_old=delete_old)
        if options["clear_cache"]:
            self.log.info("Clearing cache for autocompleter: %s" % (options["name"]))
            autocomp.clear_cache()
