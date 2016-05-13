import logging

from django.core.management.base import BaseCommand

from valuenetwork.valueaccounting.faircoin_utils import broadcast_tx

class Command(BaseCommand):
    help = "Broadcast new FairCoin transactions to the network."

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.info("-" * 72)
        count = broadcast_tx()
        msg = " ".join(["new tx count:", str(count)])
        logging.debug(msg)
        