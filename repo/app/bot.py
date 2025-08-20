import os, time, json, math
from datetime import datetime, timezone
import ccxt

EXCHANGE  = os.getenv("EXCHANGE", "binance")
SYMBOL    = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME = os.getenv("TIMEFRAME", "1m")
FAST      = int(os.getenv("FAST", "7"))
SLOW      = int(os.getenv("SLOW", "25"))
ORDER_USD = float(os.getenv("ORDER_SIZE_USD", "100"))
LOOP_SEC  = int(os.getenv("LOOP_SECONDS", "20"))

STATE_PATH  = os.getenv("STATE_PATH", "/data/paper_state.json")
TRADES_PATH = os.getenv("TRADES_PATH", "/data/paper_trades.json")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)

def sma(vals, n):
    if len(vals) < n: return None
    return sum(vals[-n:]) / n

def main():
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})
    state = load_json(STATE_PATH, {
        "symbol": SYMBOL,
        "position": "flat",
        "entry_price": None,
        "units": 0.0,
        "pnl_usd": 0.0,
        "last_signal": "none",
        "updated_at": now_iso()
    })
    trades = load_json(TRADES_PATH, [])

    print(f"[bot] starting paper bot on {EXCHANGE}:{SYMBOL} {TIMEFRAME} FAST={FAST} SLOW={SLOW}", flush=True)

    while True:
        try:
            candles = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
            closes = [c[4] for c in candles]
            last = closes[-1]
            s_fast = sma(closes, FAST)
            s_slow = sma(closes, SLOW)
            signal = "none"
            if s_fast and s_slow:
                if s_fast > s_slow:
                    signal = "buy"
                elif s_fast < s_slow:
                    signal = "sell"

            # Trading logic (long-only for simplicity)
            if signal == "buy" and state["position"] != "long":
                units = ORDER_USD / last
                state["position"] = "long"
                state["entry_price"] = last
                state["units"] = units
                state["last_signal"] = "buy"
                trades.append({"t": now_iso(), "type": "buy", "price": last, "units": units})
                print(f"[bot] BUY {units:.6f} @ {last}", flush=True)

            elif signal == "sell" and state["position"] == "long":
                pnl = (last - float(state["entry_price"])) * float(state["units"])
                state["pnl_usd"] = float(state["pnl_usd"]) + pnl
                trades.append({"t": now_iso(), "type": "sell", "price": last, "units": state["units"], "pnl": pnl})
                print(f"[bot] SELL {state['units']:.6f} @ {last}  pnl={pnl:.2f}  total={state['pnl_usd']:.2f}", flush=True)
                state["position"] = "flat"
                state["entry_price"] = None
                state["units"] = 0.0
                state["last_signal"] = "sell"

            # keep state updated
            state["updated_at"] = now_iso()
            save_json(STATE_PATH, state)
            save_json(TRADES_PATH, trades[-500:])  # keep last 500

        except Exception as e:
            print(f"[bot] error: {e}", flush=True)

        time.sleep(LOOP_SEC)

if __name__ == "__main__":
    main()
