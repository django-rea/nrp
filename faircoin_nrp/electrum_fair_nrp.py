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
import jsonrpclib

logger = logging.getLogger("faircoins")
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s')

my_host = "localhost"
my_port = 8069

# Send command to the daemon.
def send_command(cmd, params):
    server = jsonrpclib.Server('http://%s:%d'%(my_host, my_port))
    try:
        f = getattr(server, cmd)
    except socket.error, (value, message):
        logging.error("Can not connect to faircoin daemon. %d %s" %(value,message))
        return "ERROR"
    try:
        out = f(*params)
    except socket.error, (value, message):
        logging.error("Can not send the command %d %s" %(value,message))
        return "ERROR"
    logger.debug('send command: %s --- params: %s --- response: %s' %(cmd, params, out))
    logging.debug('send command: %s --- params: %s --- response: %s' %(cmd, params, out))
    return out

# Get the network fee
def network_fee():
    logger.critical('network_fee')
    response = send_command('fee', '')
    logger.debug('network_fee response: %s' %(response))
    logging.debug('network_fee response: %s' %(response))
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
    format_dict = [address]
    response = send_command('get_address_balance', format_dict)
    return response

#check if an address is valid
def is_valid(address):
    format_dict = [address]
    response = send_command('is_valid', format_dict)
    return response

#check if an address is from the wallet
def is_mine(address):
    format_dict = [address]
    response = send_command('is_mine', format_dict)
    return response

#read the history of an address
def get_address_history(address):
    format_dict = [address]
    response = send_command('get_address_history', format_dict)
    return response

# make a transfer from an adress of the wallet 
def make_transaction_from_address(address_origin, address_end, amount):
    format_dict = [address_origin, address_end, amount]
    response = send_command('make_transaction_from_address', format_dict)
    return response
         
def address_history_info(address, page = 0, items = 20):
    format_dict = [address, page, items]
    response = send_command('address_history_info', format_dict)
    return response

# create new address for users or any other entity
def new_fair_address(entity_id, entity = 'generic'):
    format_dict = [entity_id, entity]
    response = send_command('new_fair_address', format_dict)
    return response

def get_confirmations(tx):
    format_dict = [tx]
    response = send_command('get_confirmations', format_dict)
    return response

#Check if it is connected to the electum network
def is_connected():
    response = send_command('is_connected', '')
    return response

#Check if daemon is up and connected.
def daemon_is_up():
    response = send_command('daemon_is_up', '')
    return response

#get wallet info.
def get_wallet_info():
     response = send_command('get_wallet_info', '')
     return response
