import requests

class USSDGateway:
    @staticmethod
    def send_payment(phone_number, amount):
        # Example: Replace with real USSD gateway API call
        # response = requests.post("https://api.ussd-gateway.com/pay", json={"phone": phone_number, "amount": amount})
        # return response.json()
        return {"status": "success", "phone": phone_number, "amount": amount, "gateway": "mock"}

class BTCGateway:
    @staticmethod
    def get_balance(address):
        # Example: Use BlockCypher public API for BTC balance
        url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("final_balance", 0) / 1e8 # Convert satoshi to BTC
        return None

    @staticmethod
    def send_btc(from_privkey, to_address, amount_btc):
        # Example: Use BlockCypher API for testnet (for real, use a secure backend)
        # This is a placeholder. Real implementation should use a secure wallet backend.
        return {"status": "mock_sent", "from": "hidden", "to": to_address, "amount": amount_btc}
