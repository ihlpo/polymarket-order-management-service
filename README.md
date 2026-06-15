# Polymarket Order Management Service

A Flask-based REST API for managing orders on [Polymarket](https://polymarket.com) via the CLOB (Central Limit Order Book) client. Currently focused on BTC Up/Down 15-minute prediction markets.

## Prerequisites

- Python 3.8+
- A Polymarket account with API credentials
- USDC on Polygon (for placing orders)

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file in the project root:

   ```env
   PRIVATE_KEY=your_wallet_private_key
   FUNDER_ADDRESS=your_funder_address
   API_KEY=your_polymarket_api_key
   API_SECRET=your_polymarket_api_secret
   API_PASSPHRASE=your_polymarket_api_passphrase
   ```

   Your `FUNDER_ADDRESS` and API credentials can be found in your Polymarket account settings.

3. **Run the server**

   ```bash
   python app.py
   ```

   The server starts on port `5001`.

## API Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check server status |

### Account

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/clob/balance` | Get USDC collateral balance |
| GET | `/api/clob/openorders` | List all open orders |
| GET | `/api/clob/gettrades` | View trade history |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/clob/createorder` | Place a buy order |
| POST | `/api/clob/cancelall` | Cancel all open orders |

### Markets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/markets/current-btc-updown-15m` | Get current BTC Up/Down 15m market data |

## Usage

### Place an order

```bash
curl -X POST http://localhost:5001/api/clob/createorder \
  -H "Content-Type: application/json" \
  -d '{"outcome": "Up", "price": 0.55, "size": 10}'
```

**Body parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `outcome` | string | `"Up"` or `"Down"` (case-insensitive) |
| `price` | number | Limit price between 0 and 1 |
| `size` | number | Order size in USDC |

### Check balance

```bash
curl http://localhost:5001/api/clob/balance
```

### Cancel all orders

```bash
curl -X POST http://localhost:5001/api/clob/cancelall
```
