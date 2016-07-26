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
import socket
import logging
logger = logging.getLogger("faircoins")

#logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

# Send command to the daemon.
def send_command(cmd, params):
    import jsonrpclib
    server = jsonrpclib.Server('http://%s:%d'%(my_host, my_port))
    try:
        f = getattr(server, cmd)
    except socket.error:
        logging.error("Can not connect to the server.")
        return 1
        
    try:
        out = f(*params)
    except socket.error:
        logging.error("Can not send the command")
        return 1

    #logging.debug("sending : %s" %json.dumps(out, indent=4))
return 0

# Stop electrum
def do_stop():
    return_daemon = send_command('do_stop', '')
    return return_daemon

# get the total balance for the wallet
# Returns a tupla with 3 values: Confirmed, Unmature, Unconfirmed
def get_balance():
    return_daemon = send_command('get_balance', '')
    return return_daemon

# get the balance for a determined address
# Returns a tupla with 3 values: Confirmed, Unmature, Unconfirmed
def get_address_balance(address):
    return_daemon = send_command('get_address_balance', address)
    return return_daemon

#check if an address is valid
def is_valid(address):
    return_daemon = send_command('is_valid', address)
    return return_daemon

#check if an address is from the wallet
def is_mine(address):
    return_daemon = send_command('is_mine', address)
    return return_daemon

#read the history of an address
def get_address_history(address):
    return_daemon = send_command('get_address_history', address)
    return return_daemon

# make a transfer from an adress of the wallet 
def make_transaction_from_address(address_origin, address_end, amount):
    return_daemon = send_command('make_transaction_from_address', [address_origin, address_end, amount])
    return return_daemon
         
def address_history_info(address, page = 0, items = 20):
    return_daemon = send_command('address_history_info', [address, page, items])
    return return_daemon

# create new address for users or any other entity
def new_fair_address(entity_id, entity = 'generic'):
    return_daemon = send_command('new_fair_address', [entity_id, entity])
    return return_daemon

def get_confirmations(tx):
    return_daemon = send_command('get_confirmations', tx)
    return return_daemon

#Check if it is connected to the electum network
def is_connected():
    return_daemon = send_command('is_connected', '')
    return return_daemon

