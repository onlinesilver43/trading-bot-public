import os, json, time, traceback
from datetime import datetime, timezone
import ccxt

# ---- Paths & files (do not change) ----
DATA_DIR   = os.getenv("DATA_DIR", "/data")
STATE_PATH = os.getenv("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH= os.getenv("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))
F_CFG  = os.path.join(DATA_DIR, "bot_config.json")
F_CAND = os.path.join(DATA_DIR, "candles_with_signals.json")
F_DET  = os.path.join(DATA_DIR, "trades_detailed.json")
F_SNAP = os.path.join(DATA_DIR, "state_snapshots.json")

# ---- Env / params ----
EXCHANGE = os.getenv("EXCHANGE", "binanceus")
SYMBOL   = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME= os.getenv("TIMEFRAME", "1m")
FAST     = int(os.getenv("FAST", "7"))
SLOW     = int(os.getenv("SLOW", "25"))
CONFIRM_BARS   = int(os.getenv("CONFIRM_BARS", "2"))
MIN_HOLD_BARS  = int(os.getenv("MIN_HOLD_BARS", "3"))
THRESHOLD_PCT  = float(os.getenv("THRESHOLD_PCT", "0.003"))  # e.g. 0.0025–0.003
FEE_RATE       = float(os.getenv("FEE_RATE", "0.001"))

START_CASH_USD   = float(os.getenv("START_CASH_USD", "200"))
ORDER_SIZE_USD   = float(os.getenv("ORDER_SIZE_USD", "20"))
ORDER_PCT_EQUITY = os.getenv("ORDER_PCT_EQUITY")
ORDER_PCT_EQUITY = None if ORDER_PCT_EQUITY in (None,"","null","None") else float(ORDER_PCT_EQUITY)
MIN_TRADE_USD    = float(os.getenv("MIN_TRADE_USD", "5"))

LOOP_SEC = 5

# ---- Utils ----
def load_json(p, d):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return d

def atomic_write_json(p, obj):
    tmp = f"{p}.tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f)
    os.replace(tmp, p)

def append_json_array(path, obj):
    arr = load_json(path, [])
    arr.append(obj)
    atomic_write_json(path, arr[-2000:])  # keep it bounded

def ensure_state_defaults(s):
    s.setdefault("start_cash_usd", START_CASH_USD)
    s.setdefault("cash_usd", s["start_cash_usd"])
    s.setdefault("start_coin_units", 0.0)
    s.setdefault("coin_units", s["start_coin_units"])
    s.setdefault("fees_paid_usd", 0.0)
    s.setdefault("pnl_usd", 0.0)
    s.setdefault("unrealized_pnl_usd", 0.0)
    s.setdefault("position", "flat")   # 'long' or 'flat'
    s.setdefault("entry_price", None)
    s.setdefault("last_action", "seed")
    s.setdefault("last_signal", None)
    s.setdefault("symbol", SYMBOL)
    return s

def drop_forming(candles):
    if not candles: return [], None
    closed = candles[:-1]
    if not closed: return [], None
    return closed, closed[-1][0]

def sma(series, n):
    if len(series) < n: return [None]*len(series)
    out = [None]*(n-1)
    run = sum(series[:n]); out.append(run/n)
    for i in range(n, len(series)):
        run += series[i] - series[i-n]
        out.append(run/n)
    return out

def write_bot_config(symbol):
    info = {
        "symbol": symbol, "timeframe": TIMEFRAME,
        "fast_sma_len": FAST, "slow_sma_len": SLOW,
        "confirm_bars": CONFIRM_BARS,
        "hysteresis_bp": THRESHOLD_PCT*100.0,
        "order_size_usd": ORDER_SIZE_USD,
        "order_pct_equity": ORDER_PCT_EQUITY,
        "order_type": "market",
        "maker_fee_bp": FEE_RATE*10000, "taker_fee_bp": FEE_RATE*10000,
        "assumed_slippage_bp": 0.0, "min_notional_usd": 1.0,
        "tick_size": 0.01, "step_size": 1e-5,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    atomic_write_json(F_CFG, info)

def choose_symbol(ex, preferred):
    tries = [preferred] + (["BTC/USD"] if preferred=="BTC/USDT" else ["BTC/USDT"] if preferred=="BTC/USD" else [])
    last = None
    for sym in tries:
        try:
            raw = ex.fetch_ohlcv(sym, timeframe=TIMEFRAME, limit=10)
            closed, _ = drop_forming(raw)
            if closed: return sym
        except Exception as e:
            last = e
    raise last or RuntimeError("No OHLCV")

def iso(ts_ms): return datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).isoformat(timespec='seconds')

# ---- Paper trade engine ----
def place_buy(state, price, ts_bar):
    # sizing
    equity = float(state["cash_usd"]) + float(state["coin_units"])*price
    usd_to_spend = (equity * ORDER_PCT_EQUITY) if ORDER_PCT_EQUITY is not None else ORDER_SIZE_USD
    usd_to_spend = max(0.0, usd_to_spend)
    if usd_to_spend < MIN_TRADE_USD or usd_to_spend > state["cash_usd"]:
        return "skip", "insufficient cash/size"
    fee = usd_to_spend * FEE_RATE
    units = (usd_to_spend - fee) / price
    if units <= 0: return "skip", "calc units <= 0"

    state["cash_usd"] -= usd_to_spend
    state["coin_units"] += units
    state["fees_paid_usd"] += fee
    state["position"] = "long"
    state["entry_price"] = price
    trade = {
        "t": iso(ts_bar), "type": "buy", "price": price,
        "units": units, "fee_usd": fee, "cash_usd": state["cash_usd"],
        "coin_units": state["coin_units"]
    }
    append_json_array(TRADES_PATH, trade)
    return "ok", None

def place_sell(state, price, ts_bar):
    if state["coin_units"] <= 0: return "skip", "no position"
    gross = state["coin_units"] * price
    fee = gross * FEE_RATE
    cash = gross - fee
    entry = state.get("entry_price") or price
    pnl = (price - entry) * state["coin_units"]

    state["cash_usd"] += cash
    state["fees_paid_usd"] += fee
    state["position"] = "flat"
    state["entry_price"] = None
    trade = {
        "t": iso(ts_bar), "type": "sell", "price": price,
        "units": -state["coin_units"], "fee_usd": fee, "cash_usd": state["cash_usd"],
        "coin_units": 0.0, "pnl": pnl
    }
    state["coin_units"] = 0.0
    state["pnl_usd"] = state.get("pnl_usd",0.0) + pnl
    append_json_array(TRADES_PATH, trade)
    # detailed round-trip (minimal fields)
    append_json_array(F_DET, {
        "ts_close": iso(ts_bar), "pnl_usd": pnl, "price_close": price
    })
    return "ok", None

def main():
    global SYMBOL
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})

    # Pick a working symbol if needed
    try: SYMBOL = choose_symbol(ex, SYMBOL)
    except Exception as e: print(f"[bot] symbol probe failed: {e}", flush=True)

    state = ensure_state_defaults(load_json(STATE_PATH, {}))
    write_bot_config(SYMBOL)
    print(f"[bot] start {EXCHANGE}:{SYMBOL} tf={TIMEFRAME} F/S={FAST}/{SLOW} fee={FEE_RATE}", flush=True)

    last_trade_bar_ts = None  # cooldown reference

    while True:
        try:
            raw = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
            closed, last_ts = drop_forming(raw)
            if not closed or len(closed) < max(FAST,SLOW)+CONFIRM_BARS:
                time.sleep(LOOP_SEC); continue

            # Build candle fields on CLOSED bars
            o = [c[1] for c in closed]; h=[c[2] for c in closed]; l=[c[3] for c in closed]
            c = [c[4] for c in closed]; v=[c[5] for c in closed]
            fast = sma(c, FAST); slow = sma(c, SLOW)

            # Confirm bars: last N bars all up/down
            def confirmed_up():
                for i in range(1, CONFIRM_BARS+1):
                    if fast[-i] is None or slow[-i] is None or not (fast[-i] > slow[-i]): return False
                return True
            def confirmed_down():
                for i in range(1, CONFIRM_BARS+1):
                    if fast[-i] is None or slow[-i] is None or not (fast[-i] < slow[-i]): return False
                return True

            last_price = float(c[-1])
            spread = abs((fast[-1] or last_price) - (slow[-1] or last_price)) / last_price

            # Candles-with-signals (append once per CLOSED bar)
            append_json_array(F_CAND, {
                "ts": iso(last_ts), "o": o[-1], "h": h[-1], "l": l[-1], "c": c[-1], "v": v[-1],
                "fast": fast[-1], "slow": slow[-1],
                "signal": "buy" if confirmed_up() else "sell" if confirmed_down() else "hold"
            })

            # Snapshot once per CLOSED bar
            state = ensure_state_defaults(state)
            state["symbol"] = SYMBOL
            state["last_price"] = last_price
            state["unrealized_pnl_usd"] = (last_price - (state.get("entry_price") or last_price)) * state["coin_units"]
            state["equity_usd"] = state["cash_usd"] + state["coin_units"] * last_price
            state["updated_at"] = iso(last_ts)
            atomic_write_json(STATE_PATH, state)
            append_json_array(F_SNAP, {"ts": iso(last_ts), "equity_usd": state["equity_usd"]})

            # Cooldown: require MIN_HOLD_BARS since last trade bar
            if last_trade_bar_ts is not None:
                bars_since = sum(1 for ts, *_ in closed if ts > last_trade_bar_ts)
                if bars_since < MIN_HOLD_BARS:
                    state["last_action"] = "skip"
                    state["skip_reason"] = f"cooldown {bars_since}/{MIN_HOLD_BARS}"
                    atomic_write_json(STATE_PATH, state)
                    time.sleep(LOOP_SEC); continue

            # Hysteresis threshold gate (>= THRESHOLD_PCT)
            if spread < THRESHOLD_PCT:
                state["last_action"] = "skip"
                state["skip_reason"] = f"spread<{THRESHOLD_PCT}"
                atomic_write_json(STATE_PATH, state)
                time.sleep(LOOP_SEC); continue

            # Decide + act (paper)
            acted = False
            if confirmed_up() and state["position"] != "long":
                ok, reason = place_buy(state, last_price, last_ts)
                state["last_action"] = "buy" if ok=="ok" else "skip"
                state["skip_reason"] = None if ok=="ok" else reason
                atomic_write_json(STATE_PATH, state)
                if ok=="ok": last_trade_bar_ts = last_ts; acted = True

            elif confirmed_down() and state["position"] == "long":
                ok, reason = place_sell(state, last_price, last_ts)
                state["last_action"] = "sell" if ok=="ok" else "skip"
                state["skip_reason"] = None if ok=="ok" else reason
                atomic_write_json(STATE_PATH, state)
                if ok=="ok": last_trade_bar_ts = last_ts; acted = True

            if not acted and state.get("last_action") != "skip":
                state["last_action"] = "hold"
                state["skip_reason"] = None
                atomic_write_json(STATE_PATH, state)

            time.sleep(LOOP_SEC)

        except Exception as e:
            print(f"[bot] loop error: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            time.sleep(LOOP_SEC)
            continue

if __name__ == "__main__":
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})
    try:
        # symbol fallback so bot_config has a working symbol before loop
        try_sym = SYMBOL
        try:
            try:
                raw = ex.fetch_ohlcv(try_sym, timeframe=TIMEFRAME, limit=10)
                closed,_ = drop_forming(raw)
                if not closed:
                    raise RuntimeError("no closed candles")
            except Exception:
                try_sym = "BTC/USD" if SYMBOL=="BTC/USDT" else "BTC/USDT"
                raw = ex.fetch_ohlcv(try_sym, timeframe=TIMEFRAME, limit=10)
                closed,_ = drop_forming(raw)
            SYMBOL = try_sym
        except Exception as e:
            print(f"[bot] preflight symbol check failed: {e}", flush=True)
        write_bot_config(SYMBOL)
    except Exception as e:
        print(f"[bot] config write error: {e}", flush=True)
    main()
