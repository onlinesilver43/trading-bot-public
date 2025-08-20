import os, time, json, math
from datetime import datetime, timezone
import ccxt

# --- Params (env) ---
EXCHANGE  = os.getenv("EXCHANGE", "binanceus")
SYMBOL    = os.getenv("SYMBOL", "BTC/USDT")     # try BTC/USD if needed
TIMEFRAME = os.getenv("TIMEFRAME", "1m")
FAST      = int(os.getenv("FAST", "7"))
SLOW      = int(os.getenv("SLOW", "25"))
ORDER_USD = float(os.getenv("ORDER_SIZE_USD", "100"))
LOOP_SEC  = int(os.getenv("LOOP_SECONDS", "20"))

# Paper wallet
START_CASH_USD   = float(os.getenv("START_CASH_USD", "10000"))
START_COIN_UNITS = float(os.getenv("START_COIN_UNITS", "0"))
FEE_RATE         = float(os.getenv("FEE_RATE", "0.001"))  # 0.1%

# Guardrails (NEW)
CONFIRM_BARS   = int(os.getenv("CONFIRM_BARS", "2"))      # require signal persist N closed bars
MIN_HOLD_BARS  = int(os.getenv("MIN_HOLD_BARS", "3"))     # bars between flips
THRESHOLD_PCT  = float(os.getenv("THRESHOLD_PCT", "0.0005"))  # 0.05% min separation of MAs
MIN_TRADE_USD  = float(os.getenv("MIN_TRADE_USD", "20"))  # skip if spend below this

STATE_PATH  = os.getenv("STATE_PATH", "/data/paper_state.json")
TRADES_PATH = os.getenv("TRADES_PATH", "/data/paper_trades.json")

def now_iso(): return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception: return default

def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, indent=2)
    os.replace(tmp, path)

def sma_series(vals, n):
    if n <= 0 or len(vals) < n: return []
    out = []
    s = sum(vals[:n])
    out.append(s / n)
    for i in range(n, len(vals)):
        s += vals[i] - vals[i-n]
        out.append(s / n)
    return out

def tf_to_ms(tf:str) -> int:
    # handles e.g. "1m", "5m", "1h", "1d"
    n = int(''.join([c for c in tf if c.isdigit()]))
    unit = ''.join([c for c in tf if c.isalpha()]).lower()
    if unit == 'm': return n*60_000
    if unit == 'h': return n*3_600_000
    if unit == 'd': return n*86_400_000
    return 60_000  # default 1m

def ensure_defaults(state):
    defaults = {
        "symbol": SYMBOL, "position": "flat", "entry_price": None, "units": 0.0,
        "last_signal": "none", "pnl_usd": 0.0, "fees_paid_usd": 0.0,
        "start_cash_usd": START_CASH_USD, "start_coin_units": START_COIN_UNITS,
        "cash_usd": START_CASH_USD, "coin_units": START_COIN_UNITS,
        "last_price": None, "equity_usd": START_CASH_USD,
        "unrealized_pnl_usd": 0.0, "last_action": "init", "skip_reason": "",
        "last_trade_bar_ts": 0, "updated_at": now_iso(),
        "rules": {
            "CONFIRM_BARS": CONFIRM_BARS, "MIN_HOLD_BARS": MIN_HOLD_BARS,
            "THRESHOLD_PCT": THRESHOLD_PCT, "MIN_TRADE_USD": MIN_TRADE_USD,
            "FAST": FAST, "SLOW": SLOW, "FEE_RATE": FEE_RATE
        }
    }
    for k,v in defaults.items():
        if k not in state: state[k] = v
    state["rules"] = defaults["rules"]  # refresh visible rules
    return state

def main():
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})

    state = ensure_defaults(load_json(STATE_PATH, {}))
    trades = load_json(TRADES_PATH, [])
    tfms = tf_to_ms(TIMEFRAME)

    print(f"[bot] start {EXCHANGE}:{SYMBOL} tf={TIMEFRAME} F/S={FAST}/{SLOW} fee={FEE_RATE} "
          f"rules: confirm={CONFIRM_BARS} hold={MIN_HOLD_BARS} thr={THRESHOLD_PCT} minT={MIN_TRADE_USD}",
          flush=True)

    while True:
        try:
            candles = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
            if not candles or len(candles) < max(FAST, SLOW) + CONFIRM_BARS:
                time.sleep(LOOP_SEC); continue

            closes = [c[4] for c in candles]         # closed bars on most CCXT impls
            last_ts = candles[-1][0]
            last = closes[-1]

            fast_series = sma_series(closes, FAST)
            slow_series = sma_series(closes, SLOW)
            k = min(len(fast_series), len(slow_series))
            if k < CONFIRM_BARS:
                time.sleep(LOOP_SEC); continue

            # --- guardrails checks ---
            buy_conf  = all(fast_series[-i] > slow_series[-i] for i in range(1, CONFIRM_BARS+1))
            sell_conf = all(fast_series[-i] < slow_series[-i] for i in range(1, CONFIRM_BARS+1))
            sep = abs(fast_series[-1] - slow_series[-1]) / last
            threshold_ok = sep >= THRESHOLD_PCT

            bars_since_flip = (last_ts - int(state.get("last_trade_bar_ts", 0))) / tfms if state.get("last_trade_bar_ts", 0) else 1e9
            cooldown_ok = bars_since_flip >= MIN_HOLD_BARS

            # --- mark-to-market ---
            state["last_price"] = last
            equity = float(state["cash_usd"]) + float(state["coin_units"]) * last
            state["equity_usd"] = equity
            if state["position"] == "long" and state["entry_price"] is not None:
                est_exit = last * (1.0 - FEE_RATE)
                est_entry = float(state["entry_price"]) * (1.0 + FEE_RATE)
                state["unrealized_pnl_usd"] = (est_exit - est_entry) * float(state["units"])
            else:
                state["unrealized_pnl_usd"] = 0.0

            # --- decision logic ---
            state["skip_reason"] = ""
            signal = "none"
            if buy_conf and threshold_ok:
                signal = "buy"
            elif sell_conf and threshold_ok:
                signal = "sell"

            # BUY
            if signal == "buy" and state["position"] != "long":
                if not cooldown_ok:
                    state["skip_reason"] = f"cooldown {bars_since_flip:.1f} < {MIN_HOLD_BARS} bars"
                else:
                    spend = min(ORDER_USD, state["cash_usd"])
                    if spend < MIN_TRADE_USD:
                        state["skip_reason"] = f"min_trade ${MIN_TRADE_USD}"
                    else:
                        # include fee in affordability
                        units_afford = state["cash_usd"] / (last * (1.0 + FEE_RATE))
                        units_target = spend / last
                        units = max(0.0, min(units_target, units_afford))
                        if units <= 0:
                            state["skip_reason"] = "insufficient cash"
                        else:
                            fee_buy = units * last * FEE_RATE
                            cost = units * last + fee_buy
                            state["cash_usd"] -= cost
                            state["coin_units"] += units
                            state["position"] = "long"
                            state["entry_price"] = last
                            state["units"] = units
                            state["fees_paid_usd"] += fee_buy
                            state["last_signal"] = "buy"
                            state["last_action"] = f"BUY {units:.8f}"
                            state["last_trade_bar_ts"] = last_ts
                            trades.append({
                                "t": now_iso(), "type": "buy", "price": last, "units": units,
                                "fee_usd": fee_buy, "cash_usd": state["cash_usd"], "coin_units": state["coin_units"]
                            })
                            print(f"[bot] BUY {units:.8f} @ {last}  cash={state['cash_usd']:.2f}", flush=True)

            # SELL
            elif signal == "sell" and state["position"] == "long":
                if not cooldown_ok:
                    state["skip_reason"] = f"cooldown {bars_since_flip:.1f} < {MIN_HOLD_BARS} bars"
                else:
                    units = float(state["units"])
                    if units > 0:
                        fee_sell = units * last * FEE_RATE
                        proceeds = units * last - fee_sell
                        state["cash_usd"] += proceeds
                        state["coin_units"] -= units
                        pnl = (last * (1.0 - FEE_RATE) - float(state["entry_price"]) * (1.0 + FEE_RATE)) * units
                        state["pnl_usd"] = float(state["pnl_usd"]) + pnl
                        state["fees_paid_usd"] += fee_sell
                        state["position"] = "flat"
                        state["entry_price"] = None
                        state["units"] = 0.0
                        state["last_signal"] = "sell"
                        state["last_action"] = f"SELL {units:.8f} (pnl {pnl:.2f})"
                        state["last_trade_bar_ts"] = last_ts
                        trades.append({
                            "t": now_iso(), "type": "sell", "price": last, "units": units,
                            "fee_usd": fee_sell, "pnl": pnl, "cash_usd": state["cash_usd"], "coin_units": state["coin_units"]
                        })
                        print(f"[bot] SELL {units:.8f} @ {last}  pnl={pnl:.2f}  cash={state['cash_usd']:.2f}", flush=True)

            # Save
            state["updated_at"] = now_iso()
            save_json(STATE_PATH, state)
            save_json(TRADES_PATH, trades[-500:])

        except Exception as e:
            print(f"[bot] error: {e}", flush=True)

        time.sleep(LOOP_SEC)

if __name__ == "__main__":
    main()
