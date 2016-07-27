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
    return out

# Get the network fee
def network_fee():
    response = send_command('network_fee', '')
    return response

# Stop electrum
def do_stop():
    response = send_command('do_stop', '')
    return response

# get the total balance for the wallet
# Returns a tupla with 3 values: Confirmed, Unmature, Unconfirmed
def get_balance():
    response = send_command('get_balance', '')
    return response

# get the balance for a determined address
# Returns a tupla with 3 values: Confirmed, Unmature, Unconfirmed
def get_address_balance(address):
    response = send_command('get_address_balance', address)
    return response

#check if an address is valid
def is_valid(address):
    response = send_command('is_valid', address)
    return response

#check if an address is from the wallet
def is_mine(address):
    response = send_command('is_mine', address)
    return response

#read the history of an address
def get_address_history(address):
    response = send_command('get_address_history', address)
    return response

# make a transfer from an adress of the wallet 
def make_transaction_from_address(address_origin, address_end, amount):
    response = send_command('make_transaction_from_address', [address_origin, address_end, amount])
    return response
         
def address_history_info(address, page = 0, items = 20):
    response = send_command('address_history_info', [address, page, items])
    return response

# create new address for users or any other entity
def new_fair_address(entity_id, entity = 'generic'):
    response = send_command('new_fair_address', [entity_id, entity])
    return response

def get_confirmations(tx):
    response = send_command('get_confirmations', tx)
    return response

#Check if it is connected to the electum network
def is_connected():
    response = send_command('is_connected', '')
    return response

