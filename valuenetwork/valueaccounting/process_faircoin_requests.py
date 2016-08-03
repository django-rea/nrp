import sys
import time
import logging
from decimal import *

logger = logging.getLogger("faircoins")

from django.conf import settings
from django.db.models import Q

import faircoin_nrp.electrum_fair_nrp as efn

from valuenetwork.valueaccounting.models import EconomicAgent, EconomicEvent, EconomicResource
from valuenetwork.valueaccounting.lockfile import FileLock, AlreadyLocked, LockTimeout, LockFailed

#FAIRCOIN_DIVISOR = int(1000000)

def init_electrum_fair():
    #import pdb; pdb.set_trace()
    try:
        assert(efn.daemon_is_up())
    except:
        #handle failure better here
        msg = "Can not init Electrum Network. Exiting."
        assert False, msg
        
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
    
def create_address_for_agent(agent):
    #import pdb; pdb.set_trace()
    address = None
    try:
        address = efn.new_fair_address(
            entity_id = agent.nick, 
            entity = agent.agent_type.name,
            )
    except Exception:
        _, e, _ = sys.exc_info()
        logger.critical("an exception occurred in creating a FairCoin address: {0}".format(e))
    return address
    
def create_address_for_resource(resource):
    agent = resource.owner()
    address = create_address_for_agent(agent)
    if address:
        resource.digital_currency_address = address
        resource.save()
        return True
    else:
        msg = " ".join(["Failed to get a FairCoin address for", agent.name])
        logger.warning(msg)
        return False
    
def create_requested_addresses():
    try:
        requests = EconomicResource.objects.filter(
            digital_currency_address="address_requested")

        msg = " ".join(["new FairCoin address requests count:", str(requests.count())])
        logger.debug(msg)
    except Exception:
        _, e, _ = sys.exc_info()
        logger.critical("an exception occurred in retrieving FairCoin address requests: {0}".format(e))
        return "failed to get FairCoin address requests"
        
    if requests:
        init_electrum_fair()
        logger.debug("broadcast_tx ready to process FairCoin address requests")
        for resource in requests:
            result = create_address_for_resource(resource)
            
        msg = " ".join(["created", str(requests.count()), "new faircoin addresses."])
    else:
        msg = "No new faircoin address requests to process."
    return msg
    
def broadcast_tx():
    #import pdb; pdb.set_trace()
        
    try:
        events = EconomicEvent.objects.filter(
            digital_currency_tx_state="new").order_by('pk')
        events = events.filter(
            Q(event_type__name='Give')|Q(event_type__name='Distribution'))
        msg = " ".join(["new FairCoin event count:", str(events.count())])
        logger.debug(msg)
    except Exception:
        _, e, _ = sys.exc_info()
        logger.critical("an exception occurred in retrieving events: {0}".format(e))
        logger.warning("releasing lock because of error...")
        lock.release()
        logger.debug("released.")
        return "failed to get events"
        
    try:
        #import pdb; pdb.set_trace()
        successful_events = 0
        failed_events = 0
        if events:
            init_electrum_fair()
            logger.critical("broadcast_tx ready to process events")
        for event in events:
            #do we need to check for missing digital_currency_address here?
            #and create them?
            #fee = efn.network_fee() # In Satoshis
            #fee = Decimal("%s" %fee) / FAIRCOIN_DIVISOR
            if event.resource:
                if event.event_type.name=="Give":
                    address_origin = event.resource.digital_currency_address
                    address_end = event.event_reference
                elif event.event_type.name=="Distribution":
                    address_origin = event.from_agent.faircoin_address()
                    address_end = event.resource.digital_currency_address
                amount = float(event.quantity) * 1.e6 # In satoshis
                if amount < 1001:
                    event.digital_currency_tx_state = "broadcast"
                    event.digital_currency_tx_hash = "Null"
                    event.save()
                    continue

                logger.critical("about to make_transaction_from_address. Amount: %d" %(int(amount)))
                #import pdb; pdb.set_trace()
                tx_hash = None
                try:
                    tx_hash = efn.make_transaction_from_address(address_origin, address_end, int(amount))
                except Exception:
                    _, e, _ = sys.exc_info()
                    logger.critical("an exception occurred in make_transaction_from_address: {0}".format(e))
                
                if (tx_hash == "ERROR") or (not tx_hash):
                    logger.warning("ERROR tx_hash, make tx failed without raising Exception")
                    failed_events += 1
                elif tx_hash:
                    successful_events += 1
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
        """
        logger.warning("releasing lock because of error...")
        lock.release()
        logger.debug("released.")
        """
        return "failed to process events"
    """    
    logger.debug("releasing lock normally...")
    lock.release()
    logger.debug("released.")
    """
    
    if events:
        msg = " ".join(["Broadcast", str(successful_events), "new faircoin tx."])
        if failed_events:
            msg += " ".join([ str(failed_events), "events failed."])
    else:
        msg = "No new faircoin tx to process."
    return msg
