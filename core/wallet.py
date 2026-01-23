import os
import secrets
from eth_account import Account
import bitcoin
import json

class Wallet:
    def __init__(self, user_id):
        self.user_id = user_id
        self.eth_address = None
        self.eth_private_key = None
        self.btc_address = None
        self.btc_private_key = None
        self.create_wallets()

    def create_wallets(self):
        # Ethereum wallet
        acct = Account.create(secrets.token_hex(32))
        self.eth_address = acct.address
        self.eth_private_key = acct.key.hex()

        # Bitcoin wallet
        key = bitcoin.random_key()
        self.btc_private_key = key
        self.btc_address = bitcoin.privtopub(key)

    def get_wallet_info(self):
        return {
            'eth_address': self.eth_address,
            'btc_address': self.btc_address
        }

    def get_private_keys(self):
        return {
            'eth_private_key': self.eth_private_key,
            'btc_private_key': self.btc_private_key
        }

    @staticmethod
    def get_wallet(user_id):
        wallet_path = os.path.join('data', f'wallet_{user_id}.json')
        if not os.path.exists(wallet_path):
            return None
        with open(wallet_path, 'r') as f:
            data = json.load(f)
        wallet = Wallet()
        wallet.btc_address = data.get('btc_address')
        wallet.btc_private_key = data.get('btc_private_key')
        wallet.eth_address = data.get('eth_address')
        wallet.eth_private_key = data.get('eth_private_key')
        return wallet
