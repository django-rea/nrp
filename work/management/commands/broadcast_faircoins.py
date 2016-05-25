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

from valuenetwork.valueaccounting.broadcast import *

class Command(BaseCommand):
    help = "Send new FairCoin address and transaction requests to the network."

    def handle(self, *args, **options):
        logger.info("-" * 72)
        
        try:
            lock = acquire_lock()
        except Exception:
            _, e, _ = sys.exc_info()
            logger.critical("an exception occurred in acquire_lock: {0}".format(e))
            
        if lock:
            
            try:
                msg = create_requested_addresses()
                logger.info(msg)
            except Exception:
                _, e, _ = sys.exc_info()
                logger.critical("an exception occurred in create_requested_addresses: {0}".format(e))
             
            try:
                msg = broadcast_tx()
                logger.info(msg)
            except Exception:
                _, e, _ = sys.exc_info()
                logger.critical("an exception occurred in broadcast_tx: {0}".format(e))
                
            logger.debug("releasing lock normally...")
            #shd this be in broadcast.py?
            lock.release()
            logger.debug("released.")
            
