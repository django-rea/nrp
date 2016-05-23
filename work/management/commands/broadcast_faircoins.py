import time
import logging

from logging.handlers import TimedRotatingFileHandler
from django.conf import settings

logger = logging.getLogger("broadcasting")
logger.setLevel(logging.DEBUG)
fhpath = "/".join([settings.PROJECT_ROOT, "broadcast.log",])
fh = TimedRotatingFileHandler(fhpath,
                            when="d",
                            interval=1,
                            backupCount=7)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)

from django.core.management.base import BaseCommand

from valuenetwork.valueaccounting.broadcast import broadcast_tx

class Command(BaseCommand):
    help = "Broadcast new FairCoin transactions to the network."

    def handle(self, *args, **options):
        logger.info("-" * 72)
        try:
            msg = broadcast_tx()
        except Exception:
            _, e, _ = sys.exc_info()
            logger.critical("an exception occurred in broadcast_tx: {0}".format(e))
       
        logger.info(msg)
