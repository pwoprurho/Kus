import requests

class USSDGateway:
    @staticmethod
    def send_payment(phone_number, amount):
        # Example: Replace with real USSD gateway API call
        # response = requests.post("https://api.ussd-gateway.com/pay", json={"phone": phone_number, "amount": amount})
        # return response.json()
        return {"status": "success", "phone": phone_number, "amount": amount, "gateway": "mock"}

    @staticmethod
    def get_balance():
        # Mock balance check
        return {"status": "success", "balance": 1000, "currency": "USD"}

    @staticmethod
    def send_btc(from_privkey, to_address, amount_btc):
        # Example: Use BlockCypher API for testnet (for real, use a secure backend)
        # This is a placeholder. Real implementation should use a secure wallet backend.
        return {"status": "mock_sent", "from": "hidden", "to": to_address, "amount": amount_btc}

class BTCGateway:
    def __init__(self, btc_address):
        self.btc_address = btc_address

    def get_balance(self):
        # Use BlockCypher API for BTC balance
        url = f'https://api.blockcypher.com/v1/btc/main/addrs/{self.btc_address}/balance'
        try:
            resp = requests.get(url)
            data = resp.json()
            return data.get('final_balance', 0) / 1e8  # Convert satoshi to BTC
        except Exception as e:
            return f'Error: {e}'

    def send_btc(self, private_key, to_address, amount_btc):
        # Mock sending BTC for now
        return {
            'status': 'success',
            'txid': 'mock_txid',
            'to': to_address,
            'amount': amount_btc
        }
