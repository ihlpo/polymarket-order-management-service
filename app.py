import os
import time
import json
import sys
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType, OpenOrderParams, OrderArgs
from py_clob_client.order_builder.constants import BUY

# Load environment variables from .env file
load_dotenv()

# --- Environment Variable Check ---
required_env_vars = ["PRIVATE_KEY", "FUNDER_ADDRESS", "API_KEY", "API_SECRET", "API_PASSPHRASE"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    sys.exit(f"Error: Missing required environment variables: {', '.join(missing_vars)}")


app = Flask(__name__)

# --- CLOB Client Setup ---

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137 # Polygon
PK = os.environ["PRIVATE_KEY"]
FUNDER = os.environ["FUNDER_ADDRESS"] # Found in Polymarket Settings

api_creds = ApiCreds(
    api_key=os.environ["API_KEY"],
    api_secret=os.environ["API_SECRET"],
    api_passphrase=os.environ["API_PASSPHRASE"]
)

# Initialize with your private key
client = ClobClient(
    host=HOST,
    key=PK, 
    chain_id=CHAIN_ID,
    creds=api_creds,
    signature_type=2,
    funder=FUNDER
)

# Set L2 credentials 
client.set_api_creds(api_creds)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/api/clob/balance', methods=['GET'])
def get_balance():
    """
    Endpoint to fetch the user's balance using the py-clob-client.
    The credentials are read from environment variables on the server.
    """

    # COLLATERAL refers to USDC on Polymarket
    try:
        # COLLATERAL = USDC
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        resp = client.get_balance_allowance(params)
        
        print(f"Success! Sending Balance")
        return jsonify(resp)
        
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clob/openorders', methods=['GET'])
def get_open_orders():
    """
    Endpoint to fetch the user's open orders using the py-clob-client.
    """
    try:
        open_orders = client.get_orders(OpenOrderParams())
        
        if not open_orders:
            return jsonify({"message": "No open orders found"}), 200
        
        return jsonify(open_orders)
            
    except Exception as e:
        print(f"Error fetching open orders: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clob/gettrades', methods=['GET'])
def view_trade_history():
    try:
        # Fetches your recent filled trades
        trades = client.get_trades()
        
        if not trades:
            return jsonify({"message": "No trades found"}), 200
        
        return jsonify(trades)
    except Exception as e:
        print(f"Error fetching trades: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clob/createorder', methods=['POST'])
def create_order():
    data = request.get_json()

    # 2. Extract specific fields
    outcome = data.get('outcome')  # e.g., "Up" or "Down"
    price = data.get('price')
    size = data.get('size')

    if not all([outcome, price, size]):
        return jsonify({"success": False, "error": "Missing required fields: outcome, price, size"}), 400

    try:
        price_float = float(price)
        size_float = float(size)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Price and size must be valid numbers"}), 400

    try:
        # 1. Fetch the latest market data to get the token_id
        token_map, _ = _get_latest_btc_market_data()

        # 2. Find the token_id for the desired outcome (case-insensitive)
        token_id = token_map.get(outcome.lower())
        if not token_id:
            valid_outcomes = list(token_map.keys())
            return jsonify({"success": False, "error": f"Invalid outcome '{outcome}'. Must be one of {valid_outcomes}"}), 400

        # 3. Create and Post the order
        print(f"Placing order for outcome '{outcome}' with token_id: {token_id}")
        resp = client.create_and_post_order(OrderArgs(
            price=price_float,
            size=size_float,
            side=BUY,
            token_id=token_id
        ))

        print(resp)
        return jsonify(resp)

    except FileNotFoundError as e:
        print(f"Error creating order: {e}")
        return jsonify({"success": False, "error": f"Could not create order. Market not found: {e}"}), 404
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error creating order: {e}")
        return jsonify({"success": False, "error": f"Could not create order. Error fetching market data: {e}"}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clob/cancelall', methods=['POST'])
def cancel_all():
    try:
        resp = client.cancel_all()

        print(resp)

        return jsonify(resp)

    except Exception as e:
        print(f"Error canceling orders: {e}")
        return jsonify({"error": str(e)}), 500


def _get_latest_btc_market_data():
    """
    Helper function to fetch and parse the latest BTC Up/Down 15m market data.
    Returns a map of outcomes to token IDs, and the full market data.
    """
    INTERVAL = 15 * 60
    current_now = time.time()
    last_15_epoch = (current_now // INTERVAL) * INTERVAL
    slug = f"btc-updown-15m-{int(last_15_epoch)}"
    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        market_data = response.json()

        clob_token_ids_str = market_data.get("clobTokenIds")
        outcomes_str = market_data.get("outcomes")

        if not clob_token_ids_str or not outcomes_str:
            raise ValueError("clobTokenIds or outcomes not found in market data")

        clob_token_ids = json.loads(clob_token_ids_str)
        outcomes = json.loads(outcomes_str)

        # Create a mapping of outcome (lowercase) to token_id
        token_map = {outcomes[i].lower(): clob_token_ids[i] for i in range(len(outcomes))}

        return token_map, market_data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # Raise a more specific error for the calling function to handle
            raise FileNotFoundError(f"Market with slug '{slug}' not found.")
        raise e


@app.route('/api/markets/current-btc-updown-15m', methods=['GET'])
def get_btc_updown_market():
    """
    Fetches the latest BTC Up/Down 15m market data from the Polymarket gamma API.
    """
    try:
        token_map, market_data = _get_latest_btc_market_data()

        # Print the token IDs to the console
        print(f"Market Slug: {market_data.get('slug')}")

        print(f"CLOB Token IDs: {list(token_map.values())}")

        return jsonify(market_data)

    except FileNotFoundError as e:
        print(f"Market not found: {e}")
        return jsonify({"error": str(e)}), 404
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error fetching/processing market data: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


if __name__ == '__main__':
    # Runs the Flask development server
    app.run(debug=True, port=5001)
