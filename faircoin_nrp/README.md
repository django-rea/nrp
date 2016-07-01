# faircoin_nrp
faircoins payments for nrp

El objetivo de éste proyecto es proporcionar un interface muy sencillo que trabaje con la cartera electrum-fair de forma que sea fácil integrar operaciones con FairCoins en cualquier aplicación. Ha sido creado para integrar FairCoin en NRP desarrollado por http://mikorizal.org , pero dada su naturaleza puede ser utilizado en cualquier aplicación.

La versión de electrum-fair usada es la 2.3.3. Simplemente cambiando la línea import electrum-fair debería de ser capaz de usar bitcoins o cualquier otra criptomoneda a la que se haya portado la cartera electrum.

Files

    -- electrum_fair_nrp.py: The library file
    -- electrum-fair-nrp.conf: wallet settings
          [electrum]
              wallet_path = Path to the file of the wallet. If the file does not exist, init() will create one the first time is called.
              seed = A valid seed for electrum. Seeds in different languages than english can not work. Only used to create the wallet, can be deleted later.
              password = The wallet's password. Used when creating the wallet and making transfers.

          [network]
              fee = 1000 ; In satoshis ( 1000 satoshis = 0.001 FAI) The fee of the FairCoin network to make a single transaction, is substracted to the total amount in a transfer. This is for debugging purpouses, this param should not be changed.

Basic functions

    -- init()
        Starts the electrum network.
        Creates the wallet if not created before. 
        Must be called before any function.

    -- get_balance_address(address)
        address is a wallet's address.
        Returns the number of FairCoins in a single address.

    -- make_transaction_from_address(address_origin, address_end, amount)
        Creates, signs and broadcasts a transaction from address_origin to address_end.
        address_origin: A wallet's address where the funds go out.
        address_end: A FairCoin's valid address where the funds will arrive.
        amount: The number of FairCoins of the transaction.
        Returns False on failure (for example NotEnoughFunds) or the hash of the transaction if success.

    -- address_history_info(address)
        Return list with info of last 10 transactions of the address history.
        address is a wallet's address.

    -- def new_fair_address(entity_id, entity = 'generic')
        Create new address for users or any other entity. 
        Return a new address labeled or False if there's no network connection. 
        The label is for debugging proposals. It's like 'entity: id'
        We can label like "user: 213" or "user: pachamama" or "order: 67".

Usage

    * Install the electrum-fair wallet in your system:
          - Install the following packages on your system: sudo apt-get install python-pip python-qt4
          - sudo pip install https://electrum.fair-coin.org/download/Electrum-fair-2.3.3.tar.gz
    * Setup your wallet in the file electrum-fair-nrp.conf.
    * Import the electrum_fair_nrp.py file in your project.
    * Call the init() function.
    * Use the wallet calling functions. 

Contributors

    Xavip https://github.com/XaviP
    Bob Haugen https://github.com/bhaugen
    Santi https://github.com/Punto0

    This is a colaborative project from FairCoop and Freedom Coop
