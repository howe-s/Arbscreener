import requests
from web3 import Web3
# Public Free RPC Endpoint (Infura or any other public endpoint)
public_rpc_url = "https://mainnet.ethereum.org"
w3 = Web3(Web3.HTTPProvider(public_rpc_url))
rpc_url = w3


# Function to generate raw transaction data (simplified example)
def create_raw_transaction():
    # Replace with the actual transaction data
    raw_transaction = {
        "from": "0xYourAddress",
        "to": "0xRecipientAddress",
        "value": hex(int(0.1 * 10 ** 18)),  # Sending 0.1 ETH
        "gas": hex(21000),  # Standard gas limit for ETH transfer
        "gasPrice": hex(int(20 * 10 ** 9)),  # Gas price in Wei (20 Gwei)
        "nonce": hex(0),  # Replace with the actual nonce of your account
    }
    return raw_transaction


# Encode the transaction to raw format
def encode_raw_transaction(transaction):
    # Simplified: Use `web3` or another library to generate raw TX
    # Here we are hardcoding for example purposes
    raw_tx = "0xf86b808504a817c80082520894d46e8dd67c5d32be8058bb8eb970870f0724456880de0b6b3a76400008026a0b2a8bcde92c63c8b6d489e7c12504cfe42adfb4a3677cc2601226ed947b32b0da0165f63fb9c12ae08f3ef88eaf9e4b60ec6f2d632bd2cd1e1e1deda4c8e5da0b"
    return raw_tx


# Main function to estimate gas using ShapeShift API
def estimate_gas_with_shapesift(raw_tx):
    api_url = "https://api.shapeshift.com/api/v1/gas/estimate"
    headers = {"Content-Type": "application/json"}
    payload = {"rawTx": raw_tx}

    response = requests.post(api_url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}


# Example usage
if __name__ == "__main__":
    raw_tx = encode_raw_transaction(create_raw_transaction())
    gas_estimate = estimate_gas_with_shapesift(raw_tx)
    print("Gas Estimate:", gas_estimate)
