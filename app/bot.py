import os, time, json
from datetime import datetime, timezone
import ccxt

EXCHANGE  = os.getenv("EXCHANGE", "binanceus")
SYMBOL    = os.getenv("SYMBOL", "BTC/USDT")   # on binanceus you can also use BTC/USD
TIMEFRAME = os.getenv("TIMEFRAME", "1m")
FAST      = int(os.getenv("FAST", "7"))
SLOW      = int(os.getenv("SLOW", "25"))
ORDER_USD = float(os.getenv("ORDER_SIZE_USD", "100"))
LOOP_SEC  = int(os.getenv("LOOP_SECONDS", "20"))

# Paper wallet params
START_CASH_USD   = float(os.getenv("START_CASH_USD", "10000"))
START_COIN_UNITS = float(os.getenv("START_COIN_UNITS", "0"))
FEE_RATE         = float(os.getenv("FEE_RATE", "0.001"))  # 0.1% default

STATE_PATH  = os.getenv("STATE_PATH", "/data/paper_state.json")
TRADES_PATH = os.getenv("TRADES_PATH", "/data/paper_trades.json")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception: return default

def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, indent=2)
    os.replace(tmp, path)

def sma(vals, n):
    if len(vals) < n: return None
    return sum(vals[-n:]) / n

def ensure_defaults(state):
    defaults = {
        "symbol": SYMBOL, "position": "flat", "entry_price": None, "units": 0.0,
        "last_signal": "none", "pnl_usd": 0.0, "fees_paid_usd": 0.0,
        "start_cash_usd": START_CASH_USD, "start_coin_units": START_COIN_UNITS,
        "cash_usd": START_CASH_USD, "coin_units": START_COIN_UNITS,
        "last_price": None, "equity_usd": START_CASH_USD + START_COIN_UNITS * 0.0,
        "updated_at": now_iso()
    }
    for k,v in defaults.items():
        if k not in state: state[k] = v
    return state

def main():
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})

    state = ensure_defaults(load_json(STATE_PATH, {}))
    trades = load_json(TRADES_PATH, [])

    print(f"[bot] start {EXCHANGE}:{SYMBOL} tf={TIMEFRAME} FAST={FAST} SLOW={SLOW} fee={FEE_RATE}", flush=True)

    while True:
        try:
            candles = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
            closes = [c[4] for c in candles]
            last = closes[-1]
            s_fast = sma(closes, FAST)
            s_slow = sma(closes, SLOW)

            # Update marks
            state["last_price"] = last
            state["equity_usd"] = float(state["cash_usd"]) + float(state["coin_units"]) * last

            # Signal
            signal = "none"
            if s_fast is not None and s_slow is not None:
                if s_fast > s_slow: signal = "buy"
                elif s_fast < s_slow: signal = "sell"

            # Long-only toggle with wallet + fees
            if signal == "buy" and state["position"] != "long":
                max_units_afford = state["cash_usd"] / (last * (1.0 + FEE_RATE))
                target_units = ORDER_USD / last
                units = min(target_units, max_units_afford)
                if units > 0:
                    fee_buy = units * last * FEE_RATE
                    cost = units * last + fee_buy
                    state["cash_usd"] -= cost
                    state["coin_units"] += units
                    state["position"] = "long"
                    state["entry_price"] = last
                    state["units"] = units
                    state["last_signal"] = "buy"
                    state["fees_paid_usd"] += fee_buy
                    trades.append({
                        "t": now_iso(), "type": "buy", "price": last, "units": units,
                        "fee_usd": fee_buy, "cash_usd": state["cash_usd"], "coin_units": state["coin_units"]
                    })
                    print(f"[bot] BUY {units:.8f} @ {last}  cash={state['cash_usd']:.2f}", flush=True)
                else:
                    print("[bot] buy skipped (insufficient cash)", flush=True)

            elif signal == "sell" and state["position"] == "long":
                units = float(state["units"])
                if units > 0:
                    fee_sell = units * last * FEE_RATE
                    proceeds = units * last - fee_sell
                    state["cash_usd"] += proceeds
                    state["coin_units"] -= units
                    # PnL versus entry including both sides’ fees
                    pnl = (last * (1.0 - FEE_RATE) - float(state["entry_price"]) * (1.0 + FEE_RATE)) * units
                    state["pnl_usd"] = float(state["pnl_usd"]) + pnl
                    state["fees_paid_usd"] += fee_sell
                    trades.append({
                        "t": now_iso(), "type": "sell", "price": last, "units": units,
                        "fee_usd": fee_sell, "pnl": pnl, "cash_usd": state["cash_usd"], "coin_units": state["coin_units"]
                    })
                    print(f"[bot] SELL {units:.8f} @ {last}  pnl={pnl:.2f}  cash={state['cash_usd']:.2f}", flush=True)
                state["position"] = "flat"
                state["entry_price"] = None
                state["units"] = 0.0
                state["last_signal"] = "sell"

            state["updated_at"] = now_iso()
            save_json(STATE_PATH, state)
            save_json(TRADES_PATH, trades[-500:])
        except Exception as e:
            print(f"[bot] error: {e}", flush=True)

        time.sleep(LOOP_SEC)

if __name__ == "__main__":
    main()
