#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# Faircoin Payment For NRP
# Copyright (C) 2015-2016 santi@punto0.org -- FairCoop 
#
# This version is based on https://github.com/Punto0/faircoin_nrp
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import time, sys, os
import logging
logger = logging.getLogger("faircoins")

from django.conf import settings

import electrum_fair
from electrum_fair import util
from electrum_fair.util import NotEnoughFunds
electrum_fair.set_verbosity(True)

import ConfigParser
config = ConfigParser.ConfigParser()
#this is because cron needs full paths
conf_path = "/".join([settings.PROJECT_ROOT, "faircoin_nrp/electrum-fair-nrp.conf",])

config.read(conf_path)

wallet_path = config.get('electrum','wallet_path')

seed = config.get('electrum','seed')
password = config.get('electrum', 'password')
network_fee = config.get('network','fee')

#logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

wallet = False
network = False
cmd_wallet = False

# Stop electrum
def do_stop():
    network.stop_daemon()
    if network.is_connected():
        time.sleep(1) 
    logger.debug("Stopping")    
    return "ok"

# get the total balance for the wallet
# Returns a tupla with 3 values: Confirmed, Unmature, Unconfirmed
def get_balance():
    return wallet.get_balance()

# get the balance for a determined address
# Returns a tupla with 3 values: Confirmed, Unmature, Unconfirmed
def get_address_balance(address):
    return wallet.get_balance([address])

#check if an address is valid
def is_valid(address):
    return cmd_wallet.validateaddress(address)

#check if an address is from the wallet
def is_mine(address):
    return wallet.is_mine(address)

#read the history of an address
def get_address_history(address):
    return wallet.get_address_history(address)

# make a transfer from an adress of the wallet 
def make_transaction_from_address(address_origin, address_end, amount):
    if not is_mine(address_origin): 
        logger.error("The address %s does not belong to this wallet" %address_origin)
        return False
    if not is_valid(address_end):
        logger.error("The address %s is not a valid faircoin address" %address_end)
        return False

    inputs = [address_origin]
    coins = wallet.get_spendable_coins(domain = inputs)
    #print coins
    amount_total = ( 1.e6 * float(amount) ) - float(network_fee)
    amount_total = int(amount_total)

    if amount_total > 0:
        output = [('address', address_end, int(amount_total))] 
    else:
        logger.error("Amount negative: %s" %(amount_total) )
        return False
    try:
        tx = wallet.make_unsigned_transaction(coins, output, change_addr=address_origin)
    except NotEnoughFunds:
	        logger.error("Not enough funds confirmed to make the transaction. %s %s %s" %wallet.get_addr_balance(address_origin))
                return False
    wallet.sign_transaction(tx, password)
    rec_tx_state, rec_tx_out = wallet.sendtx(tx)
    if rec_tx_state:
         logger.info("SUCCESS. The transaction has been broadcasted.")
         return rec_tx_out
    else:
         logger.error("Sending %s fairs to the address %s" %(amount_total, address_end ) )
         return False
         
def address_history_info(address, page = 0, items = 20):
    """Return list with info of last 20 transactions of the address history"""
    return_history = []
    history = cmd_wallet.getaddresshistory(address)
    tx_num = 0
    for i, one_transaction in enumerate(history, start = page * items):
        tx_num += 1
        if tx_num > items:
            return return_history
        raw_transaction = cmd_wallet.gettransaction(one_transaction['tx_hash'])
        info_transaction = raw_transaction.deserialize()
        return_history.append({'tx_hash': one_transaction['tx_hash'], 'tx_data': info_transaction})
    return return_history

# create new address for users or any other entity
def new_fair_address(entity_id, entity = 'generic'):
    """ Return a new address labeled or False if there's no network connection. 
    The label is for debugging proposals. It's like 'entity: id'
    We can label like "user: 213" or "user: pachamama" or "order: 67".
    """
    while network.is_connected():
        new_address = wallet.create_new_address()
        check_label = wallet.get_label(new_address)
        check_history = cmd_wallet.getaddresshistory(new_address)
        # It checks if address is labeled or has history yet, a gap limit protection. 
        # This can be removed when we have good control of gap limit.     
        if not check_label[0] and not check_history:
            wallet.set_label(new_address, entity + ': ' + str(entity_id))
            return new_address
    return False

def get_confirmations(tx):
    """Return the number of confirmations of a monitored transaction
    and the timestamp of the last confirmation (or None if not confirmed)."""
    return wallet.get_confirmations(tx)

#Check if it is connected to the electum network
def is_connected():
        return network.is_connected()

# init the wallet
def init():
    global wallet
    global network
    global cmd_wallet
    logger.debug("Starting electrum-fair-nrp")
    # start network
    c = electrum_fair.SimpleConfig({'wallet_path':wallet_path})
    daemon_socket = electrum_fair.daemon.get_daemon(c, True)
    network = electrum_fair.NetworkProxy(daemon_socket, config)
    network.start()
    n = 0
    # wait until connected
    while (network.is_connecting() and (n < 100)):
        time.sleep(0.5)
        n = n + 1

    if not network.is_connected():
        logger.error("Can not init Electrum Network. Exiting.")
        sys.exit(1)

    # create wallet
    storage = electrum_fair.WalletStorage(wallet_path)
    if not storage.file_exists:
        logger.debug("creating wallet file")
        wallet = electrum_fair.wallet.Wallet.from_seed(seed, password, storage)
    else:
        wallet = electrum_fair.wallet.Wallet(storage)
    
    wallet.synchronize = lambda: None # prevent address creation by the wallet
    #wallet.change_gap_limit(100)  
    wallet.start_threads(network)
    cmd_wallet = electrum_fair.commands.Commands(c, wallet, network)  
    
