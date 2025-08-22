import os, json, time, traceback
from datetime import datetime, timezone
import ccxt

# ---- Paths (unchanged) ----
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
THRESHOLD_PCT  = float(os.getenv("THRESHOLD_PCT", "0.003"))  # 0.30%
FEE_RATE       = float(os.getenv("FEE_RATE", "0.001"))

START_CASH_USD   = float(os.getenv("START_CASH_USD", "200"))
ORDER_SIZE_USD   = float(os.getenv("ORDER_SIZE_USD", "20"))
ORDER_PCT_EQUITY = os.getenv("ORDER_PCT_EQUITY")
ORDER_PCT_EQUITY = None if ORDER_PCT_EQUITY in (None,"","null","None") else float(ORDER_PCT_EQUITY)
MIN_TRADE_USD    = float(os.getenv("MIN_TRADE_USD", "5"))

# ---- Stacking knobs ----
STACK_FLOOR_USD  = float(os.getenv("STACK_FLOOR_USD", "200"))   # never let cash drop below this
SKIM_PROFIT_PCT  = float(os.getenv("SKIM_PROFIT_PCT", "0.15"))  # % of realized profit to stash

LOOP_SEC = 5

def tf_to_ms(tf: str) -> int:
    tf = (tf or '').strip().lower()
    if tf.endswith('ms'): return int(tf[:-2])
    if tf.endswith('s'):  return int(tf[:-1]) * 1000
    if tf.endswith('m'):  return int(tf[:-1]) * 60_000
    if tf.endswith('h'):  return int(tf[:-1]) * 3_600_000
    if tf.endswith('d'):  return int(tf[:-1]) * 86_400_000
    # default 1m
    return 60_000

def sleep_until_next_close(tf_ms: int, last_closed_ts_ms: int):
    import time
    # next close is last_closed_ts + tf_ms
    target = (last_closed_ts_ms or 0) + int(tf_ms)
    now_ms = int(time.time()*1000)
    # small guard so we wake just after the close
    delay = max(0.0, (target - now_ms)/1000.0 + 0.5)
    time.sleep(delay)


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
    atomic_write_json(path, arr[-2000:])  # bound size

def ensure_state_defaults(s):
    s.setdefault("start_cash_usd", START_CASH_USD)
    s.setdefault("cash_usd", s["start_cash_usd"])
    s.setdefault("coin_units", 0.0)         # total = stash + trade
    s.setdefault("trade_coin_units", 0.0)   # tradable
    s.setdefault("stash_coin_units", 0.0)   # never sold
    s["coin_units"] = float(s["stash_coin_units"]) + float(s["trade_coin_units"])
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

def iso(ts_ms): return datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).isoformat(timespec='seconds')

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
        "stack_floor_usd": STACK_FLOOR_USD,
        "skim_profit_pct": SKIM_PROFIT_PCT,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    atomic_write_json(F_CFG, info)

def ensure_expected_files_exist(state):
    """Idempotently ensure config + trade files exist."""
    try:
        if not os.path.isfile(F_CFG):
            write_bot_config(state.get("symbol") or SYMBOL)
        for f in (TRADES_PATH, F_DET, F_CAND, F_SNAP):
            if not os.path.isfile(f):
                atomic_write_json(f, [])
    except Exception as e:
        print(f"[bot] ensure files error: {e}", flush=True)

def reseed_if_missing(state, last_price=None):
    """If state files were deleted (Hard Reset), re-seed fresh."""
    missing = [p for p in (STATE_PATH, TRADES_PATH, F_CFG) if not os.path.isfile(p)]
    if not missing:
        return state, False
    state = ensure_state_defaults({})
    if last_price is not None:
        state["last_price"] = float(last_price)
    state["position"] = "flat"; state["entry_price"] = None
    write_bot_config(SYMBOL)
    atomic_write_json(STATE_PATH, state)
    atomic_write_json(TRADES_PATH, [])
    atomic_write_json(F_DET, [])
    return state, True

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

# ---- Sizing & paper execution ----
def available_cash_for_buy(state):
    return max(0.0, float(state["cash_usd"]) - STACK_FLOOR_USD)

def size_usd(state, price):
    equity = float(state["cash_usd"]) + float(state["coin_units"]) * price
    want = (equity * ORDER_PCT_EQUITY) if ORDER_PCT_EQUITY is not None else ORDER_SIZE_USD
    return max(0.0, min(want, available_cash_for_buy(state)))

def place_buy(state, price, ts_bar):
    usd_to_spend = size_usd(state, price)
    if usd_to_spend < MIN_TRADE_USD:
        return "skip", "insufficient cash/size"
    fee = usd_to_spend * FEE_RATE
    units = (usd_to_spend - fee) / price
    if units <= 0: return "skip", "calc units <= 0"

    state["cash_usd"] -= usd_to_spend
    state["fees_paid_usd"] += fee
    state["trade_coin_units"] += units
    state["coin_units"] = state["stash_coin_units"] + state["trade_coin_units"]
    state["position"] = "long"
    state["entry_price"] = price

    append_json_array(TRADES_PATH, {
        "t": iso(ts_bar), "type": "buy", "price": price,
        "units": units, "fee_usd": fee, "cash_usd": state["cash_usd"],
        "coin_units": state["coin_units"]
    })
    return "ok", None

def place_sell_with_skim(state, price, ts_bar):
    trade_units = float(state["trade_coin_units"])
    if trade_units <= 0: return "skip", "no tradable position"

    gross = trade_units * price
    fee = gross * FEE_RATE
    cash_net = gross - fee
    entry = state.get("entry_price") or price
    pnl = (price - entry) * trade_units

    state["cash_usd"] += cash_net
    state["fees_paid_usd"] += fee
    state["pnl_usd"] = state.get("pnl_usd", 0.0) + pnl

    append_json_array(TRADES_PATH, {
        "t": iso(ts_bar), "type": "sell", "price": price,
        "units": -trade_units, "fee_usd": fee, "cash_usd": state["cash_usd"],
        "coin_units": state["coin_units"], "pnl": pnl
    })
    append_json_array(F_DET, {"ts_close": iso(ts_bar), "pnl_usd": pnl, "price_close": price})

    state["trade_coin_units"] = 0.0
    state["position"] = "flat"
    state["entry_price"] = None

    if pnl > 0 and SKIM_PROFIT_PCT > 0.0:
        skim_usd_desired = pnl * SKIM_PROFIT_PCT
        max_skim_allowed = max(0.0, state["cash_usd"] - STACK_FLOOR_USD)
        skim_usd = min(skim_usd_desired, max_skim_allowed)
        if skim_usd >= MIN_TRADE_USD / 2:
            stash_units = skim_usd / price
            state["cash_usd"] -= skim_usd
            state["stash_coin_units"] += stash_units
            state["coin_units"] = state["stash_coin_units"] + state["trade_coin_units"]
            append_json_array(TRADES_PATH, {
                "t": iso(ts_bar), "type": "skim_to_stash", "price": price,
                "units": stash_units, "fee_usd": 0.0, "cash_usd": state["cash_usd"],
                "coin_units": state["coin_units"], "note": f"skim {SKIM_PROFIT_PCT*100:.1f}% of profit"
            })

    return "ok", None

def main():
    global SYMBOL
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})

    try: SYMBOL = choose_symbol(ex, SYMBOL)
    except Exception as e: print(f"[bot] symbol probe failed: {e}", flush=True)

    state = ensure_state_defaults(load_json(STATE_PATH, {}))
    write_bot_config(SYMBOL)
    ensure_expected_files_exist(state)
    print(f"[bot] start {EXCHANGE}:{SYMBOL} tf={TIMEFRAME} F/S={FAST}/{SLOW} fee={FEE_RATE}", flush=True)

    last_trade_bar_ts = None

    while True:
        try:
            raw = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
            closed, last_ts = drop_forming(raw)
            if not closed or len(closed) < max(FAST,SLOW)+CONFIRM_BARS:
                sleep_until_next_close(tf_ms, last_ts); continue

            o=[c[1] for c in closed]; h=[c[2] for c in closed]; l=[c[3] for c in closed]
            c=[c[4] for c in closed]; v=[c[5] for c in closed]
            fast = sma(c, FAST); slow = sma(c, SLOW)
            last_price = float(c[-1])

            # Hard Reset self-heal
            state, _ = reseed_if_missing(state, last_price)

            # Confirm
            def confirmed_up():
                for i in range(1, CONFIRM_BARS+1):
                    if fast[-i] is None or slow[-i] is None or not (fast[-i] > slow[-i]): return False
                return True
            def confirmed_down():
                for i in range(1, CONFIRM_BARS+1):
                    if fast[-i] is None or slow[-i] is None or not (fast[-i] < slow[-i]): return False
                return True

            # Hysteresis
            anchor = slow[-1] if slow[-1] is not None else last_price
            spread = abs((fast[-1] if fast[-1] is not None else last_price) - anchor) / last_price

            # Diagnostics aligned to CLOSED bar
            append_json_array(F_CAND, {
                "ts": iso(last_ts), "o": o[-1], "h": h[-1], "l": l[-1], "c": c[-1], "v": v[-1],
                "fast": fast[-1], "slow": slow[-1],
                "signal": "buy" if confirmed_up() else "sell" if confirmed_down() else "hold"
            })

            # Snapshot
            state = ensure_state_defaults(state)
            state["symbol"] = SYMBOL
            state["last_price"] = last_price
            state["unrealized_pnl_usd"] = (
                (last_price - (state.get("entry_price") or last_price)) * float(state["trade_coin_units"])
            )
            state["equity_usd"] = float(state["cash_usd"]) + float(state["coin_units"]) * last_price
            state["updated_at"] = iso(last_ts)
            atomic_write_json(STATE_PATH, state)
            append_json_array(F_SNAP, {"ts": iso(last_ts), "equity_usd": state["equity_usd"]})
            ensure_expected_files_exist(state)

            # Consistency: no coins => flat
            if float(state.get("coin_units", 0.0)) <= 0:
                state["position"] = "flat"; state["entry_price"] = None
                atomic_write_json(STATE_PATH, state)

            # Cooldown
            if last_trade_bar_ts is not None:
                bars_since = sum(1 for ts, *_ in closed if ts > last_trade_bar_ts)
                if bars_since < MIN_HOLD_BARS:
                    state["last_action"] = "skip"; state["skip_reason"] = f"cooldown {bars_since}/{MIN_HOLD_BARS}"
                    atomic_write_json(STATE_PATH, state)
                    sleep_until_next_close(tf_ms, last_ts); continue

            # Threshold
            if spread < THRESHOLD_PCT:
                state["last_action"] = "skip"; state["skip_reason"] = f"spread<{THRESHOLD_PCT}"
                atomic_write_json(STATE_PATH, state)
                sleep_until_next_close(tf_ms, last_ts); continue

            # Decide + act
            acted = False
            if confirmed_up() and state["position"] != "long":
                ok, reason = place_buy(state, last_price, last_ts)
                state["last_action"] = "buy" if ok=="ok" else "skip"
                state["skip_reason"] = None if ok=="ok" else reason
                atomic_write_json(STATE_PATH, state)
                if ok=="ok": last_trade_bar_ts = last_ts; acted = True
            elif confirmed_down() and state["position"] == "long":
                ok, reason = place_sell_with_skim(state, last_price, last_ts)
                state["last_action"] = "sell" if ok=="ok" else "skip"
                state["skip_reason"] = None if ok=="ok" else reason
                atomic_write_json(STATE_PATH, state)
                if ok=="ok": last_trade_bar_ts = last_ts; acted = True

            if not acted and state.get("last_action") != "skip":
                state["last_action"] = "hold"; state["skip_reason"] = None
                atomic_write_json(STATE_PATH, state)

            sleep_until_next_close(tf_ms, last_ts)

        except Exception as e:
            print(f"[bot] loop error: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            sleep_until_next_close(tf_ms, last_ts)
            continue

if __name__ == "__main__":
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})
    try:
        try_sym = SYMBOL
        try:
            raw = ex.fetch_ohlcv(try_sym, timeframe=TIMEFRAME, limit=10)
            closed,_ = drop_forming(raw)
            if not closed: raise RuntimeError("no closed candles")
        except Exception:
            try_sym = "BTC/USD" if SYMBOL=="BTC/USDT" else "BTC/USDT"
            raw = ex.fetch_ohlcv(try_sym, timeframe=TIMEFRAME, limit=10)
            closed,_ = drop_forming(raw)
        SYMBOL = try_sym
    except Exception as e:
        print(f"[bot] preflight symbol check failed: {e}", flush=True)
    write_bot_config(SYMBOL)
    # Ensure empty trades files exist before entering loop
    ensure_expected_files_exist(ensure_state_defaults(load_json(STATE_PATH, {})))
    main()
