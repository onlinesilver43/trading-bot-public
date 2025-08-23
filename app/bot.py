import os, json, time, traceback
from datetime import datetime, timezone, timedelta
import ccxt

# ---------- Config loader (profiles + strict allowlist overrides) ----------
PROFILE_DIR = os.path.join(os.path.dirname(__file__), "config", "strategies")
# Try both /app/config/strategies (in image) and /config/strategies (bind-mount fallback)
if not os.path.isdir(PROFILE_DIR):
    alt = "/config/strategies"
    if os.path.isdir(alt):
        PROFILE_DIR = alt

ALLOW_ENV_OVERRIDES = {"STRAT_PROFILE", "TIMEFRAME", "ORDER_PCT_EQUITY"}

def load_profile():
    name = os.getenv("STRAT_PROFILE", "blended_1000")
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Cannot load profile '{name}': {e}")
    required = [
        "EXCHANGE","SYMBOL","TIMEFRAME","FAST","SLOW","CONFIRM_BARS","MIN_HOLD_BARS",
        "THRESHOLD_PCT","FEE_RATE","SLIPPAGE_BP","START_CASH_USD","MIN_TRADE_USD",
        "RETAIN_PCT_UP","RETAIN_PCT_CHOP","RETAIN_PCT_DOWN","CASH_FLOOR_PCT",
        "REBALANCE_DAYS","REBALANCE_MAX_STASH_PCT","REBALANCE_TARGET_STASH_PCT"
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise RuntimeError(f"Profile '{name}' missing keys: {missing}")
    # safe overrides
    for k in ALLOW_ENV_OVERRIDES:
        if k == "STRAT_PROFILE":  # already used
            continue
        v = os.getenv(k)
        if v is None or v == "":
            continue
        if k == "ORDER_PCT_EQUITY":
            cfg[k] = float(v)
        elif k == "TIMEFRAME":
            cfg[k] = v
    cfg["_profile_name"] = name
    return cfg

CFG = load_profile()

# ---------- Paths (do not change) ----------
DATA_DIR   = os.getenv("DATA_DIR", "/data")
STATE_PATH = os.getenv("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH= os.getenv("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))
F_CFG  = os.path.join(DATA_DIR, "bot_config.json")
F_CAND = os.path.join(DATA_DIR, "candles_with_signals.json")
F_DET  = os.path.join(DATA_DIR, "trades_detailed.json")
F_SNAP = os.path.join(DATA_DIR, "state_snapshots.json")

# ---------- Bind config into variables ----------
EXCHANGE = CFG["EXCHANGE"]
SYMBOL   = CFG["SYMBOL"]
TIMEFRAME= CFG["TIMEFRAME"]

FAST     = int(CFG["FAST"])
SLOW     = int(CFG["SLOW"])
CONFIRM_BARS   = int(CFG["CONFIRM_BARS"])
MIN_HOLD_BARS  = int(CFG["MIN_HOLD_BARS"])
THRESHOLD_PCT  = float(CFG["THRESHOLD_PCT"])

FEE_RATE       = float(CFG.get("FEE_RATE", 0.001))
SLIPPAGE_BP    = float(CFG.get("SLIPPAGE_BP", 5))
COST_BUFFER_BP = float(CFG.get("COST_BUFFER_BP", 0))

START_CASH_USD   = float(CFG.get("START_CASH_USD", 200))
ORDER_SIZE_USD   = float(CFG.get("ORDER_SIZE_USD", 0))
ORDER_PCT_EQUITY = CFG.get("ORDER_PCT_EQUITY", None)
ORDER_PCT_EQUITY = None if ORDER_PCT_EQUITY in (None,"","null","None") else float(ORDER_PCT_EQUITY)
MIN_TRADE_USD    = float(CFG.get("MIN_TRADE_USD", 5))
STACK_FLOOR_USD  = float(CFG.get("STACK_FLOOR_USD", 0))

RETAIN_PCT_UP   = float(CFG.get("RETAIN_PCT_UP", 0.10))
RETAIN_PCT_CHOP = float(CFG.get("RETAIN_PCT_CHOP", 0.03))
RETAIN_PCT_DOWN = float(CFG.get("RETAIN_PCT_DOWN", 0.00))
CASH_FLOOR_PCT  = float(CFG.get("CASH_FLOOR_PCT", 0.40))

TREND_SLOPE_BARS       = int(CFG.get("TREND_SLOPE_BARS", 20))
SLOPE_MIN_PCT_PER_BAR  = float(CFG.get("SLOPE_MIN_PCT_PER_BAR", 0.0001))

REBALANCE_DAYS              = int(CFG.get("REBALANCE_DAYS", 30))
REBALANCE_MAX_STASH_PCT     = float(CFG.get("REBALANCE_MAX_STASH_PCT", 0.70))
REBALANCE_TARGET_STASH_PCT  = float(CFG.get("REBALANCE_TARGET_STASH_PCT", 0.60))

SKIM_PROFIT_PCT = float(CFG.get("SKIM_PROFIT_PCT", 0))
# no-dust retain guard (USD) — if retained value < this, do not stash
MIN_RETAIN_USD  = float(CFG.get("MIN_RETAIN_USD", 2.0))

# ---------- Helpers ----------
def tf_to_ms(tf: str) -> int:
    tf = (tf or '').strip().lower()
    if tf.endswith('ms'): return int(tf[:-2])
    if tf.endswith('s'):  return int(tf[:-1]) * 1000
    if tf.endswith('m'):  return int(tf[:-1]) * 60_000
    if tf.endswith('h'):  return int(tf[:-1]) * 3_600_000
    if tf.endswith('d'):  return int(tf[:-1]) * 86_400_000
    return 60_000
tf_ms = tf_to_ms(TIMEFRAME)

def sleep_until_next_close(tf_ms: int, last_closed_ts_ms: int):
    target = (last_closed_ts_ms or 0) + int(tf_ms)
    now_ms = int(time.time()*1000)
    delay = max(0.0, (target - now_ms)/1000.0 + 0.5)
    time.sleep(delay)

def load_json(p, d):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return d

def atomic_write_json(p, obj):
    tmp = f"{p}.tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f)
    os.replace(tmp, p)

def append_json_array(path, obj, cap=2000):
    arr = load_json(path, [])
    arr.append(obj)
    atomic_write_json(path, arr[-cap:])

def ensure_state_defaults(s):
    s.setdefault("start_cash_usd", START_CASH_USD)
    s.setdefault("cash_usd", s["start_cash_usd"])
    s.setdefault("trade_coin_units", 0.0)
    s.setdefault("stash_coin_units", 0.0)
    s["coin_units"] = float(s["stash_coin_units"]) + float(s["trade_coin_units"])
    s.setdefault("fees_paid_usd", 0.0)
    s.setdefault("pnl_usd", 0.0)
    s.setdefault("unrealized_pnl_usd", 0.0)
    s.setdefault("position", "flat")
    s.setdefault("entry_price", None)
    s.setdefault("last_action", "seed")
    s.setdefault("last_signal", None)
    s.setdefault("last_rebalance_ts", None)
    s.setdefault("symbol", SYMBOL)
    s.setdefault("profile", CFG.get("_profile_name"))
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
        "min_hold_bars": MIN_HOLD_BARS,
        "hysteresis_bp": round(THRESHOLD_PCT*100.0, 4),
        "order_size_usd": ORDER_SIZE_USD,
        "order_pct_equity": ORDER_PCT_EQUITY,
        "maker_fee_bp": FEE_RATE*10000, "taker_fee_bp": FEE_RATE*10000,
        "assumed_slippage_bp": SLIPPAGE_BP, "min_notional_usd": 1.0,
        "tick_size": 0.01, "step_size": 1e-5,
        "stack_floor_usd": STACK_FLOOR_USD,
        "retain_pct_up": RETAIN_PCT_UP,
        "retain_pct_chop": RETAIN_PCT_CHOP,
        "retain_pct_down": RETAIN_PCT_DOWN,
        "cash_floor_pct": CASH_FLOOR_PCT,
        "rebalance_days": REBALANCE_DAYS,
        "rebalance_max_stash_pct": REBALANCE_MAX_STASH_PCT,
        "rebalance_target_stash_pct": REBALANCE_TARGET_STASH_PCT,
        "profile": CFG.get("_profile_name"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    atomic_write_json(F_CFG, info)

def ensure_expected_files_exist(state):
    try:
        if not os.path.isfile(F_CFG):
            write_bot_config(state.get("symbol") or SYMBOL)
        for f in (TRADES_PATH, F_DET, F_CAND, F_SNAP):
            if not os.path.isfile(f):
                atomic_write_json(f, [])
    except Exception as e:
        print(f"[bot] ensure files error: {e}", flush=True)

def reseed_if_missing(state, last_price=None):
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

# ---------- Sizing & paper execution ----------
def available_cash_for_buy(state):
    return max(0.0, float(state["cash_usd"]) - STACK_FLOOR_USD)

def equity_now(state, price):
    return float(state.get("cash_usd", 0.0)) + (float(state.get("coin_units", 0.0)) * price)

def size_usd(state, price):
    eq = equity_now(state, price)
    want = (eq * ORDER_PCT_EQUITY) if ORDER_PCT_EQUITY is not None else ORDER_SIZE_USD
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

def place_sell_with_stack_dynamic(state, price, ts_bar, regime):
    trade_units = float(state.get("trade_coin_units", 0.0))
    if trade_units <= 0: return "skip", "no tradable position"

    base_pct = {"up": RETAIN_PCT_UP, "chop": RETAIN_PCT_CHOP, "down": RETAIN_PCT_DOWN}.get(regime, RETAIN_PCT_CHOP)

    eq = equity_now(state, price)
    cash = float(state.get("cash_usd", 0.0))
    floor_cash = CASH_FLOOR_PCT * eq
    effective_pct = base_pct if cash >= floor_cash else 0.0

    # compute retain; drop if under MIN_RETAIN_USD ("no-dust retain")
    retain_units = max(0.0, min(trade_units, trade_units * effective_pct))
    if retain_units * price < MIN_RETAIN_USD:
        retain_units = 0.0

    if retain_units > 0:
        state["trade_coin_units"] = float(trade_units - retain_units)
        state["stash_coin_units"] = float(state.get("stash_coin_units", 0.0)) + retain_units
        state["coin_units"] = state["stash_coin_units"] + state["trade_coin_units"]
        append_json_array(TRADES_PATH, {
            "t": iso(ts_bar), "type": "retain_to_stash", "price": price,
            "units": retain_units, "fee_usd": 0.0,
            "cash_usd": state.get("cash_usd"), "coin_units": state["coin_units"],
            "note": f"regime={regime}, pct={effective_pct:.3f}, min_retain_usd={MIN_RETAIN_USD}"
        })

    sell_units = float(state["trade_coin_units"])
    if sell_units <= 0:
        state["position"] = "flat"; state["entry_price"] = None
        return "ok", None

    gross = sell_units * price
    fee = gross * FEE_RATE
    cash_net = gross - fee
    entry = state.get("entry_price") or price
    pnl = (price - entry) * sell_units

    state["cash_usd"] = float(state.get("cash_usd", 0.0)) + cash_net
    state["fees_paid_usd"] = float(state.get("fees_paid_usd", 0.0)) + fee
    state["pnl_usd"] = float(state.get("pnl_usd", 0.0)) + pnl

    append_json_array(TRADES_PATH, {
        "t": iso(ts_bar), "type": "sell", "price": price,
        "units": -sell_units, "fee_usd": fee, "cash_usd": state["cash_usd"],
        "coin_units": state.get("stash_coin_units", 0.0), "pnl": pnl,
        "note": f"regime={regime}"
    })

    state["trade_coin_units"] = 0.0
    state["coin_units"] = float(state.get("stash_coin_units", 0.0))
    state["position"] = "flat"
    state["entry_price"] = None
    return "ok", None

def maybe_monthly_rebalance(state, price, ts_bar_iso):
    if REBALANCE_DAYS <= 0: return
    def _parse_iso(x):
        try:
            return datetime.fromisoformat(x.replace("Z","+00:00")) if "Z" in x else datetime.fromisoformat(x)
        except Exception:
            return None
    now_dt = _parse_iso(ts_bar_iso) or datetime.now(timezone.utc)
    last_iso = state.get("last_rebalance_ts")
    if last_iso:
        last_dt = _parse_iso(last_iso)
        if last_dt and (now_dt - last_dt) < timedelta(days=REBALANCE_DAYS):
            return

    eq = equity_now(state, price)
    if eq <= 0:
        state["last_rebalance_ts"] = now_dt.isoformat(timespec='seconds'); return

    stash_units = float(state.get("stash_coin_units", 0.0))
    stash_val = stash_units * price
    if eq > 0 and stash_val/eq <= REBALANCE_MAX_STASH_PCT:
        state["last_rebalance_ts"] = now_dt.isoformat(timespec='seconds'); return

    target_stash_val = REBALANCE_TARGET_STASH_PCT * eq
    excess_val = max(0.0, stash_val - target_stash_val)
    if excess_val < MIN_TRADE_USD:
        state["last_rebalance_ts"] = now_dt.isoformat(timespec='seconds'); return

    sell_units = min(stash_units, excess_val / price)
    gross = sell_units * price
    fee = gross * FEE_RATE
    cash_net = gross - fee
    state["stash_coin_units"] = stash_units - sell_units
    state["coin_units"] = state["stash_coin_units"] + state.get("trade_coin_units", 0.0)
    state["cash_usd"] = float(state.get("cash_usd", 0.0)) + cash_net
    state["fees_paid_usd"] = float(state.get("fees_paid_usd", 0.0)) + fee

    append_json_array(TRADES_PATH, {
        "t": ts_bar_iso, "type": "rebalance_sell", "price": price,
        "units": -sell_units, "fee_usd": fee, "cash_usd": state["cash_usd"],
        "coin_units": state["coin_units"],
        "note": f"trim stash to {REBALANCE_TARGET_STASH_PCT:.2f} equity"
    })
    state["last_rebalance_ts"] = now_dt.isoformat(timespec='seconds')

# ---------- Strategy helpers ----------
def confirmed_up(fast, slow):
    for i in range(1, CONFIRM_BARS+1):
        if fast[-i] is None or slow[-i] is None or not (fast[-i] > slow[-i]): return False
    return True

def confirmed_down(fast, slow):
    for i in range(1, CONFIRM_BARS+1):
        if fast[-i] is None or slow[-i] is None or not (fast[-i] < slow[-i]): return False
    return True

def slope_pct_per_bar(series, bars):
    if len(series) < bars+1: return 0.0
    a = series[-bars-1]
    b = series[-1]
    if a is None or b is None or a == 0: return 0.0
    return (b - a) / abs(a) / bars

def detect_regime(fast, slow):
    s_fast = slope_pct_per_bar(fast, TREND_SLOPE_BARS)
    s_slow = slope_pct_per_bar(slow, TREND_SLOPE_BARS)
    up = confirmed_up(fast, slow) and s_fast > SLOPE_MIN_PCT_PER_BAR and s_slow >= 0
    down = confirmed_down(fast, slow) and s_fast < -SLOPE_MIN_PCT_PER_BAR and s_slow <= 0
    if up: return "up"
    if down: return "down"
    return "chop"

# ---------- Candle append de-dupe ----------
def append_candle_if_new(obj):
    arr = load_json(F_CAND, [])
    if arr and isinstance(arr[-1], dict) and arr[-1].get("ts") == obj.get("ts"):
        return  # same closed bar already logged
    append_json_array(F_CAND, obj)

# ---------- Main loop ----------
def main():
    global SYMBOL
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})

    try:
        SYMBOL = choose_symbol(ex=ex, preferred=SYMBOL)
    except Exception as e:
        print(f"[bot] symbol probe failed: {e}", flush=True)

    state = ensure_state_defaults(load_json(STATE_PATH, {}))
    write_bot_config(SYMBOL)
    ensure_expected_files_exist(state)
    print(f"[bot] start {EXCHANGE}:{SYMBOL} tf={TIMEFRAME} F/S={FAST}/{SLOW} fee={FEE_RATE} profile={CFG.get('_profile_name')}", flush=True)

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
            last_price = float(c[-1]); ts_iso = iso(last_ts)

            state, _ = reseed_if_missing(state, last_price)

            # Hysteresis against same-side repeats
            anchor = slow[-1] if slow[-1] is not None else last_price
            spread = abs((fast[-1] if fast[-1] is not None else last_price) - anchor) / last_price
            if spread <= THRESHOLD_PCT:
                same_side = ("buy" if confirmed_up(fast,slow) else "sell" if confirmed_down(fast,slow) else None)
                if same_side and same_side == state.get("last_signal"):
                    state["last_action"] = "skip"; state["skip_reason"] = f"hysteresis<{THRESHOLD_PCT}"
                    atomic_write_json(STATE_PATH, state)
                    sleep_until_next_close(tf_ms, last_ts); continue

            # Diagnostics (closed-bar aligned) with de-dupe
            append_candle_if_new({
                "ts": ts_iso, "o": o[-1], "h": h[-1], "l": l[-1], "c": c[-1], "v": v[-1],
                "fast": fast[-1], "slow": slow[-1],
                "signal": "buy" if confirmed_up(fast,slow) else "sell" if confirmed_down(fast,slow) else "hold"
            })

            # Snapshot
            state = ensure_state_defaults(state)
            state["symbol"] = SYMBOL
            state["last_price"] = last_price
            state["unrealized_pnl_usd"] = ((last_price - (state.get("entry_price") or last_price)) *
                                           float(state.get("trade_coin_units",0.0)))
            state["coin_units"] = float(state.get("stash_coin_units",0.0)) + float(state.get("trade_coin_units",0.0))
            state["equity_usd"] = equity_now(state, last_price)
            state["updated_at"] = ts_iso
            atomic_write_json(STATE_PATH, state)
            append_json_array(F_SNAP, {"ts": ts_iso, "equity_usd": state["equity_usd"]})
            ensure_expected_files_exist(state)

            # Consistency: no coins => flat
            if float(state.get("trade_coin_units", 0.0)) <= 0 and state.get("position") != "flat":
                state["position"] = "flat"; state["entry_price"] = None
                atomic_write_json(STATE_PATH, state)

            # Cooldown
            if last_trade_bar_ts is not None:
                bars_since = sum(1 for ts, *_ in closed if ts > last_trade_bar_ts)
                if bars_since < MIN_HOLD_BARS:
                    state["last_action"] = "skip"; state["skip_reason"] = f"cooldown {bars_since}/{MIN_HOLD_BARS}"
                    atomic_write_json(STATE_PATH, state)
                    sleep_until_next_close(tf_ms, last_ts); continue

            # Regime
            regime = detect_regime(fast, slow)

            # Actions
            acted = False
            if confirmed_up(fast, slow) and state["position"] != "long":
                ok, reason = place_buy(state, last_price, last_ts)
                state["last_signal"] = "buy"
                state["last_action"] = "buy" if ok=="ok" else "skip"
                state["skip_reason"] = None if ok=="ok" else reason
                atomic_write_json(STATE_PATH, state)
                if ok=="ok": last_trade_bar_ts = last_ts; acted = True
            elif confirmed_down(fast, slow) and state["position"] == "long":
                ok, reason = place_sell_with_stack_dynamic(state, last_price, last_ts, regime)
                state["last_signal"] = "sell"
                state["last_action"] = "sell" if ok=="ok" else "skip"
                state["skip_reason"] = None if ok=="ok" else reason
                atomic_write_json(STATE_PATH, state)
                if ok=="ok": last_trade_bar_ts = last_ts; acted = True

            if not acted and state.get("last_action") != "skip":
                state["last_action"] = "hold"; state["skip_reason"] = None
                atomic_write_json(STATE_PATH, state)

            maybe_monthly_rebalance(state, last_price, ts_iso)
            atomic_write_json(STATE_PATH, state)

            sleep_until_next_close(tf_ms, last_ts)

        except Exception as e:
            print(f"[bot] loop error: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            sleep_until_next_close(tf_ms, last_ts)
            continue

# secondary choose_symbol also used in main guard
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

if __name__ == "__main__":
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})
    try:
        try_sym = SYMBOL
        try:
            raw = ex.fetch_ohlcv(try_sym, timeframe=TIMEFRAME, limit=10); closed,_ = drop_forming(raw)
            if not closed: raise RuntimeError("no closed candles")
        except Exception:
            try_sym = "BTC/USD" if SYMBOL=="BTC/USDT" else "BTC/USDT"
            raw = ex.fetch_ohlcv(try_sym, timeframe=TIMEFRAME, limit=10); closed,_ = drop_forming(raw)
        SYMBOL = try_sym
    except Exception as e:
        print(f"[bot] preflight symbol check failed: {e}", flush=True)
    write_bot_config(SYMBOL)
    ensure_expected_files_exist(ensure_state_defaults(load_json(STATE_PATH, {})))
    main()
