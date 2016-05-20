import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# create file handler which logs even debug messages
fhpath = '/home/bob/.virtualenvs/fcx/valuenetwork/faircoin_utils.log'
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

from django.conf import settings

import faircoin_nrp.electrum_fair_nrp as efn

from valuenetwork.valueaccounting.models import EconomicEvent
from valuenetwork.valueaccounting.lockfile import FileLock, AlreadyLocked, LockTimeout, LockFailed

def init_electrum_fair():
    #import pdb; pdb.set_trace()
    try:
        if not efn.network:
            efn.init()
        else:
            if not efn.network.is_connected():
                efn.init()
    except:
        #handle failure better here
        msg = "Can not init Electrum Network. Exiting."
        assert False, msg
        
def create_address_for_agent(agent):
    #import pdb; pdb.set_trace()
    init_electrum_fair()
    wallet = efn.wallet
    address = None
    address = efn.new_fair_address(
        entity_id = agent.nick, 
        entity = agent.agent_type.name,
        )
    return address
    
def network_fee():
    return efn.network_fee
    
def send_fake_faircoins(address_origin, address_end, amount):
    import time
    tx = str(time.time())
    broadcasted = True
    print "sent fake faircoins"
    return tx, broadcasted
    
def get_address_history(address):
    init_electrum_fair()
    wallet = efn.wallet
    return wallet.get_address_history(address)

def get_address_balance(address):
    init_electrum_fair()
    return efn.get_address_balance(address)
    
def is_valid(address):
    init_electrum_fair()
    return efn.is_valid(address)
    
def get_confirmations(tx):
    init_electrum_fair()
    return efn.get_confirmations(tx)
    
def acquire_lock():
    lock = FileLock("broadcast-faircoins")
    logger.debug("acquiring lock...")
    try:
        #lock.acquire(settings.BROADCAST_FAIRCOINS_LOCK_WAIT_TIMEOUT)
        lock.acquire(1)
    except AlreadyLocked:
        logger.warning("lock already in place. quitting.")
        return False
    except LockTimeout:
        logger.warning("waiting for the lock timed out. quitting.")
        return False
    logger.debug("lock acquired.")
    return lock
        
def broadcast_tx():
    #import pdb; pdb.set_trace()
    logger.debug("broadcast_tx b4 acquire_lock")
    
    try:
        lock = acquire_lock()
    except Exception:
        _, e, _ = sys.exc_info()
        logger.critical("an exception occurred in acquire_lock: {0}".format(e))
        return "lock failed"
        
    if not lock:
        return "lock failed"
    
    logger.debug("broadcast_tx not locking for test")
    
    #problem: this log message was the last one that appeared
    logger.debug("broadcast_tx after acquire_lock")
    
    try:
        events = EconomicEvent.objects.filter(
            digital_currency_tx_state="new",
            event_type__name="Give")
        msg = " ".join(["new tx count b4 init_electrum_fair:", str(events.count())])
        logger.debug(msg)
    except Exception:
        _, e, _ = sys.exc_info()
        logger.critical("an exception occurred in retrieving events: {0}".format(e))
        logger.warning("releasing lock because of error...")
        lock.release()
        logger.debug("released.")
        return "failed to get events"
        
    try:
        if events:
            init_electrum_fair()
            logger.debug("broadcast_tx ready to process events")
        for event in events:
            if event.resource:
                address_origin = event.resource.digital_currency_address
                address_end = event.event_reference
                amount = event.quantity
                logger.debug("about to make_transaction_from_address")
                
                #import pdb; pdb.set_trace()
                #problem: this never happened when run from cron over many tests
                try:
                    tx_hash = efn.make_transaction_from_address(address_origin, address_end, amount)
                except Exception:
                    _, e, _ = sys.exc_info()
                    logger.critical("an exception occurred in make_transaction_from_address: {0}".format(e))
                
                if tx_hash:
                    event.digital_currency_tx_state = "broadcast"
                    event.digital_currency_tx_hash = tx_hash
                    event.save()
                    transfer = event.transfer
                    if transfer:
                        revent = transfer.receive_event()
                        if revent:
                            revent.digital_currency_tx_state = "broadcast"
                            revent.digital_currency_tx_hash = tx_hash
                            revent.save()
                    msg = " ".join([ "**** sent tx", tx_hash, "amount", str(amount), "from", address_origin, "to", address_end ])
                    logger.debug(msg)
    except Exception:
        _, e, _ = sys.exc_info()
        logger.critical("an exception occurred in processing events: {0}".format(e))
        logger.warning("releasing lock because of error...")
        lock.release()
        logger.debug("released.")
        return "failed to process events"
        
    logger.debug("releasing lock normally...")
    lock.release()
    logger.debug("released.")
    if events:
        msg = " ".join(["processed", str(events.count()), "new faircoin tx."])
    else:
        msg = "No new faircoin tx to process."
    return msg