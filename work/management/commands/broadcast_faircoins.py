import time
import logging
from logging.handlers import TimedRotatingFileHandler
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# create file handler which logs even debug messages
fhpath = '/home/bob/.virtualenvs/fcx/valuenetwork/broadcast_faircoins.log'
fh = TimedRotatingFileHandler(fhpath,
                            when="d",
                            interval=1,
                            backupCount=7)
fh.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
# add the handler to logger
logger.addHandler(fh)


from django.core.management.base import BaseCommand

from valuenetwork.valueaccounting.broadcast import broadcast_tx

class Command(BaseCommand):
    help = "Broadcast new FairCoin transactions to the network."

    def handle(self, *args, **options):
        #logger.info("-" * 72)
        try:
            msg = broadcast_tx()
        except Exception:
            _, e, _ = sys.exc_info()
            logger.critical("an exception occurred in broadcast_tx: {0}".format(e))
       
        logger.info(msg)
