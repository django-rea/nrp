import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('/home/bob/.virtualenvs/fcx/valuenetwork/broadcast_faircoins.log')
fh.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
# add the handler to logger
logger.addHandler(fh)


from django.core.management.base import BaseCommand

from valuenetwork.valueaccounting.faircoin_utils import broadcast_tx

class Command(BaseCommand):
    help = "Broadcast new FairCoin transactions to the network."

    def handle(self, *args, **options):
        logger.info("-" * 72)
        count = broadcast_tx()
        msg = " ".join(["new tx count:", str(count)])
        logger.info(msg)
