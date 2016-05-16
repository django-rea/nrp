import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('/home/bob/.virtualenvs/fcx/valuenetwork/faircoin_utils.log')
fh.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
# add the handler to logger
logger.addHandler(fh)

from django.conf import settings

import faircoin_nrp.electrum_fair_nrp as efn

from valuenetwork.valueaccounting.models import EconomicEvent
from valuenetwork.valueaccounting.lockfile import FileLock, AlreadyLocked, LockTimeout

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
        lock.acquire()
    except AlreadyLocked:
        logger.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logger.debug("waiting for the lock timed out. quitting.")
        return
    logger.debug("acquired.")
    return lock
        
def broadcast_tx():
    #import pdb; pdb.set_trace()
    logger.info("broadcast_tx b4 acquire_lock")
    
    #problem: no log messages appeared after acquire_lock
    #so disableled it for debugging
    #don't know if lock failed, or something there swallowed logging
    #lock = acquire_lock()
    
    logger.info("broadcast_tx not locking for test")
    
    #problem: this log message was the last one that appeared
    logger.info("broadcast_tx after acquire_lock")
    
    try:
        events = EconomicEvent.objects.filter(
            digital_currency_tx_state="new",
            event_type__name="Give")
    except:
        logger.info("error in retrieving events")
    msg = " ".join(["new tx count b4 init_electrum_fair:", str(events.count())])
    logger.info(msg)
    if events:
        init_electrum_fair()
        logger.info("broadcast_tx ready to process events")
    for event in events:
        if event.resource:
            address_origin = event.resource.digital_currency_address
            address_end = event.event_reference
            amount = event.quantity
            logger.info("about to make_transaction_from_address")
            
            #import pdb; pdb.set_trace()
            #problem: this never happened when run from cron over many tests
            tx_hash = efn.make_transaction_from_address(address_origin, address_end, amount)
            
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
                logger.info(msg)
    logger.debug("releasing lock...")
    # disabled for debugging
    #lock.release()
    logger.debug("released.")

    return events.count()