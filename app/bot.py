# app/bot.py
# Paper-trading SMA bot (closed-bar only) with guardrails & atomic state.
# Invariants: data dir & JSON filenames unchanged; symbol fallback; endpoints served by ui.py unchanged.

import os, json, time, math, tempfile, shutil, threading, traceback
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import ccxt

DATA_DIR = os.environ.get("DATA_DIR", "/srv/trading-bots/data")
os.makedirs(DATA_DIR, exist_ok=True)

# ===== Helpers =====

def now_ms() -> int:
    return int(time.time() * 1000)

def iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).isoformat()

def atomic_write_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), indent=None)
    os.replace(tmp, path)

def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def sma(values: List[float], n: int) -> Optional[float]:
    if n <= 0 or len(values) < n:
        return None
    return sum(values[-n:]) / n

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def read_env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except:
        return default

def read_env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except:
        return default

# ===== Config from .env =====

EXCHANGE = os.environ.get("EXCHANGE", "binanceus")
SYMBOL_PRIMARY = os.environ.get("SYMBOL", "BTC/USDT")
TIMEFRAME = os.environ.get("TIMEFRAME", "1m")
FAST = read_env_int("FAST", 7)
SLOW = read_env_int("SLOW", 25)
CONFIRM_BARS = read_env_int("CONFIRM_BARS", 2)
MIN_HOLD_BARS = read_env_int("MIN_HOLD_BARS", 3)
THRESHOLD_PCT = read_env_float("THRESHOLD_PCT", 0.003)
FEE_RATE = read_env_float("FEE_RATE", 0.001)
START_CASH_USD = read_env_float("START_CASH_USD", 200.0)
ORDER_SIZE_USD = read_env_float("ORDER_SIZE_USD", 20.0)
ORDER_PCT_EQUITY = os.environ.get("ORDER_PCT_EQUITY")
ORDER_PCT_EQUITY = float(ORDER_PCT_EQUITY) if ORDER_PCT_EQUITY else None
MIN_TRADE_USD = read_env_float("MIN_TRADE_USD", 5.0)

# Hardening knobs
MAX_SPREAD_BPS = read_env_int("MAX_SPREAD_BPS", 20)
MAX_CLOCK_SKEW_MS = read_env_int("MAX_CLOCK_SKEW_MS", 1500)
SLIPPAGE_SIM_BPS = read_env_int("SLIPPAGE_SIM_BPS", 3)
MAX_RETRY_ATTEMPTS = read_env_int("MAX_RETRY_ATTEMPTS", 3)
RETRY_BACKOFF_MS = read_env_int("RETRY_BACKOFF_MS", 250)

# ===== File paths =====
PAPER_STATE = os.path.join(DATA_DIR, "paper_state.json")
PAPER_TRADES = os.path.join(DATA_DIR, "paper_trades.json")
TRADES_DETAILED = os.path.join(DATA_DIR, "trades_detailed.json")
CANDLES_SIG = os.path.join(DATA_DIR, "candles_with_signals.json")
SNAPSHOTS = os.path.join(DATA_DIR, "state_snapshots.json")
BOT_CONFIG = os.path.join(DATA_DIR, "bot_config.json")

# ===== Bootstrap state =====
state = load_json(PAPER_STATE, {})
trades = load_json(PAPER_TRADES, [])
trades_detailed = load_json(TRADES_DETAILED, [])
snapshots = load_json(SNAPSHOTS, [])
candles_sig = load_json(CANDLES_SIG, [])
bot_config = load_json(BOT_CONFIG, {})

if not state:
    state = {
        "paper": True,
        "equity_usd": START_CASH_USD,
        "cash_usd": START_CASH_USD,
        "pos_qty": 0.0,
        "pos_avg": None,
        "last_action": None,
        "last_skip_reason": "boot",
        "last_trade_closed_bar_iso": None,
        "bars_since_trade": None,
        "last_closed_bar_iso": None,
        "last_processed_bar_id": None
    }
    atomic_write_json(PAPER_STATE, state)

if not bot_config:
    bot_config = {
        "exchange": EXCHANGE,
        "timeframe": TIMEFRAME,
        "symbol_requested": SYMBOL_PRIMARY,
        "symbol_effective": None,
        "fast": FAST,
        "slow": SLOW,
        "confirm_bars": CONFIRM_BARS,
        "min_hold_bars": MIN_HOLD_BARS,
        "threshold_pct": THRESHOLD_PCT,
        "fee_rate": FEE_RATE,
        "start_cash_usd": START_CASH_USD,
        "order_size_usd": ORDER_SIZE_USD,
        "order_pct_equity": ORDER_PCT_EQUITY,
        "min_trade_usd": MIN_TRADE_USD,
        "filters": {},
    }

# ===== Exchange setup & symbol fallback =====
def create_exchange():
    klass = getattr(ccxt, EXCHANGE)
    return klass({
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })

ex = create_exchange()

def resolve_symbol(sym: str) -> str:
    try:
        markets = ex.load_markets()
        if sym in markets:
            return sym
        alt = "BTC/USD" if sym == "BTC/USDT" else "BTC/USDT"
        if alt in markets:
            return alt
    except Exception:
        pass
    return sym  # as-is if lookup failed

symbol = resolve_symbol(SYMBOL_PRIMARY)
bot_config["symbol_effective"] = symbol
atomic_write_json(BOT_CONFIG, bot_config)

# ===== Confirm window utility =====
confirm_seq: List[str] = []

def push_confirm(tag: str):
    global confirm_seq
    confirm_seq.append(tag)
    if len(confirm_seq) > max(1, CONFIRM_BARS):
        confirm_seq = confirm_seq[-CONFIRM_BARS:]

def confirm_passes(tag: str) -> bool:
    if CONFIRM_BARS <= 1:
        return True if tag in ("buy","sell") else False
    if len(confirm_seq) < CONFIRM_BARS:
        return False
    return all(t == tag for t in confirm_seq)

# ===== Retry wrapper =====
def with_retries(fn, *args, **kwargs):
    delay = RETRY_BACKOFF_MS / 1000.0
    for i in range(MAX_RETRY_ATTEMPTS):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if i == MAX_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 2.0)

# ===== Core loop =====
def loop():
    global state, trades, trades_detailed, snapshots, candles_sig, ex
    last_bar_id = state.get("last_processed_bar_id")

    while True:
        try:
            # Clock skew check
            try:
                server_ms = with_retries(ex.fetch_time)
                clock_skew = abs(server_ms - now_ms())
            except Exception:
                server_ms, clock_skew = None, None

            if clock_skew is not None and clock_skew > MAX_CLOCK_SKEW_MS:
                state["last_skip_reason"] = "clock_skew"
                state["clock_skew_ms"] = clock_skew
                state["heartbeat_iso"] = iso(now_ms())
                atomic_write_json(PAPER_STATE, state)
                time.sleep(1.2)
                continue

            # Market data: candles (we only act on last CLOSED bar)
            ohlcv = with_retries(ex.fetch_ohlcv, symbol, timeframe=TIMEFRAME, limit=max(200, SLOW+5))
            if not ohlcv or len(ohlcv) < max(FAST, SLOW) + 2:
                state["last_skip_reason"] = "insufficient_candles"
                state["heartbeat_iso"] = iso(now_ms())
                atomic_write_json(PAPER_STATE, state)
                time.sleep(1.0)
                continue

            # Identify last closed bar
            last = ohlcv[-1]   # most recent bar (may be forming)
            prev = ohlcv[-2]   # last CLOSED bar
            closed_ts, open_, high, low, close, vol = prev

            # forming-bar guardrail: ensure we never act on 'last'
            last_closed_bar_id = f"{symbol}|{TIMEFRAME}|{closed_ts}"
            state["last_closed_bar_iso"] = iso(closed_ts)

            # idempotency: never act twice on same bar id
            if state.get("last_processed_bar_id") == last_closed_bar_id:
                state["last_skip_reason"] = "dup_bar_skipped"
                state["heartbeat_iso"] = iso(now_ms())
                atomic_write_json(PAPER_STATE, state)
                time.sleep(0.9)
                continue

            closes = [c[4] for c in ohlcv[:-1]]  # exclude forming
            fast = sma(closes, FAST)
            slow = sma(closes, SLOW)
            tag = "flat"
            if fast is not None and slow is not None:
                tag = "buy" if fast > slow else "sell" if fast < slow else "flat"
            push_confirm(tag)

            delta_pct = abs((fast - slow) / close) if (fast and slow and close) else 0.0
            passes_threshold = delta_pct >= THRESHOLD_PCT

            # Spread check (optional; only if ticker available)
            spread_bps = None
            try:
                tkr = with_retries(ex.fetch_ticker, symbol)
                if tkr and tkr.get("bid") and tkr.get("ask"):
                    spread_bps = (tkr["ask"] - tkr["bid"]) / ((tkr["ask"] + tkr["bid"]) / 2.0) * 1e4
            except Exception:
                pass
            if spread_bps is not None and spread_bps > MAX_SPREAD_BPS:
                skip_reason = f"wide_spread (bps={round(spread_bps,1)})"
                _post_snapshot(closed_ts, tag, fast, slow, delta_pct, passes_threshold, spread_bps, skip_reason)
                _update_state(closed_ts, skip_reason)
                time.sleep(0.9); continue

            # Cooldown bars since last trade
            bars_since_trade = None
            if state.get("last_trade_closed_bar_iso"):
                last_trade_ms = int(datetime.fromisoformat(state["last_trade_closed_bar_iso"]).timestamp()*1000)
                bars_since_trade = max(0, (closed_ts - last_trade_ms) // _bar_ms(TIMEFRAME))
            state["bars_since_trade"] = bars_since_trade

            # Decide action with all guardrails
            action, reason = "skip", None
            if tag == "flat":
                reason = "confirm_not_met"
            elif not confirm_passes(tag):
                reason = "confirm_not_met"
            elif not passes_threshold:
                reason = "below_threshold"
            elif bars_since_trade is not None and bars_since_trade < MIN_HOLD_BARS:
                reason = f"cooldown_active ({bars_since_trade}/{MIN_HOLD_BARS})"
            else:
                action = "buy" if tag == "buy" else "sell"

            # Sizing / min notional gates
            qty, notional = 0.0, 0.0
            if action in ("buy","sell"):
                equity = state.get("cash_usd", START_CASH_USD)
                if ORDER_PCT_EQUITY is not None:
                    size = clamp(equity * clamp(ORDER_PCT_EQUITY, 0.02, 0.5), MIN_TRADE_USD, max(equity, MIN_TRADE_USD))
                else:
                    size = ORDER_SIZE_USD
                notional = size
                if notional < MIN_TRADE_USD:
                    action, reason = "skip", "below_min_notional"
                else:
                    qty = notional / close
                    qty = math.floor(qty * 1e6) / 1e6
                    if qty <= 0:
                        action, reason = "skip", "qty_rounding_to_zero"

            # Execute paper fill (with slippage + fees)
            if action in ("buy","sell"):
                fill_price = close * (1 + SLIPPAGE_SIM_BPS/1e4) if action=="buy" else close * (1 - SLIPPAGE_SIM_BPS/1e4)
                fee = fill_price * qty * FEE_RATE
                pnl = 0.0
                side = action

                if side == "buy":
                    cost = fill_price * qty + fee
                    if state["cash_usd"] < cost:
                        action, reason = "skip", "insufficient_cash"
                    else:
                        prev_qty = state["pos_qty"]
                        prev_avg = state["pos_avg"] or 0.0
                        new_qty = prev_qty + qty
                        new_avg = ((prev_qty * prev_avg) + (qty * fill_price)) / new_qty if new_qty > 0 else None
                        state["pos_qty"] = new_qty
                        state["pos_avg"] = new_avg
                        state["cash_usd"] -= cost
                if action == "skip":
                    _post_snapshot(closed_ts, tag, fast, slow, delta_pct, passes_threshold, spread_bps, reason)
                    _update_state(closed_ts, reason)
                    time.sleep(0.6); continue

                if side == "sell":
                    qty_to_sell = min(state["pos_qty"], qty)
                    if qty_to_sell <= 0:
                        action, reason = "skip", "no_position"
                        _post_snapshot(closed_ts, tag, fast, slow, delta_pct, passes_threshold, spread_bps, reason)
                        _update_state(closed_ts, reason)
                        time.sleep(0.6); continue
                    entry_avg = state["pos_avg"] or close
                    realized = (fill_price - entry_avg) * qty_to_sell - (fill_price * qty_to_sell * FEE_RATE)
                    state["pos_qty"] = round(state["pos_qty"] - qty_to_sell, 6)
                    if state["pos_qty"] == 0:
                        state["pos_avg"] = None
                    state["cash_usd"] += fill_price * qty_to_sell - (fill_price * qty_to_sell * FEE_RATE)
                    pnl = realized

                # book trade records
                t = {
                    "t": iso(now_ms()),
                    "bar_iso": iso(closed_ts),
                    "side": side,
                    "qty": qty if side=="buy" else min(qty, trades_detailed[-1]["pos_after"]["qty"] if trades_detailed else qty),
                    "price": round(fill_price, 8),
                    "fee": round(fee, 8),
                    "reason": f"signal_{side}",
                }
                trades.append(t)
                atomic_write_json(PAPER_TRADES, trades)

                pos_after = {"qty": state["pos_qty"], "avg": state["pos_avg"]}
                td = {
                    "bar_iso": iso(closed_ts),
                    "side": side,
                    "qty": t["qty"],
                    "price": t["price"],
                    "fee": t["fee"],
                    "slippage_sim_bps": SLIPPAGE_SIM_BPS,
                    "delta_pct": round(delta_pct, 6),
                    "spread_bps": spread_bps,
                    "pos_after": pos_after,
                    "pnl": round(pnl, 8),
                }
                trades_detailed.append(td)
                atomic_write_json(TRADES_DETAILED, trades_detailed)

                state["last_action"] = side
                state["last_trade_closed_bar_iso"] = iso(closed_ts)
                state["last_skip_reason"] = None

            else:
                _post_snapshot(closed_ts, tag, fast, slow, delta_pct, passes_threshold, spread_bps, reason)
                _update_state(closed_ts, reason)

            # candles_with_signals append (closed bar)
            candles_sig.append({
                "t": iso(closed_ts),
                "o": open_, "h": high, "l": low, "c": close, "v": vol,
                "fast": fast, "slow": slow,
                "tag": tag
            })
            if len(candles_sig) > 5000:
                candles_sig = candles_sig[-5000:]
            atomic_write_json(CANDLES_SIG, candles_sig)

            # mark this closed bar processed (idempotent)
            state["last_processed_bar_id"] = last_closed_bar_id
            state["heartbeat_iso"] = iso(now_ms())
            mtm = (state["pos_qty"] or 0.0) * close
            state["equity_usd"] = round((state["cash_usd"] or 0.0) + mtm, 8)
            atomic_write_json(PAPER_STATE, state)

            time.sleep(0.6)

        except Exception as e:
            err = "".join(traceback.format_exc()[-400:])
            state["last_skip_reason"] = f"exchange_unavailable"
            state["error"] = str(e)
            state["heartbeat_iso"] = iso(now_ms())
            atomic_write_json(PAPER_STATE, state)
            time.sleep(1.2)

def _post_snapshot(closed_ts, tag, fast, slow, delta_pct, passes_threshold, spread_bps, skip_reason):
    global snapshots
    snapshots.append({
        "bar_iso": iso(closed_ts),
        "action": "skip" if skip_reason else ("buy" if tag=="buy" else "sell" if tag=="sell" else "flat"),
        "skip_reason": skip_reason,
        "confirm_sequence": list(confirm_seq),
        "confirm_required": CONFIRM_BARS,
        "delta_pct": round(delta_pct, 6),
        "threshold_pct": THRESHOLD_PCT,
        "spread_bps": spread_bps,
    })
    if len(snapshots) > 5000:
        snapshots = snapshots[-5000:]
    atomic_write_json(SNAPSHOTS, snapshots)

def _update_state(closed_ts, skip_reason):
    state["last_action"] = "skip"
    state["last_skip_reason"] = skip_reason
    state["last_closed_bar_iso"] = iso(closed_ts)
    state["heartbeat_iso"] = iso(now_ms())
    atomic_write_json(PAPER_STATE, state)

def _bar_ms(tf: str) -> int:
    unit = tf[-1]
    n = int(tf[:-1])
    if unit == "m": return n * 60_000
    if unit == "h": return n * 3_600_000
    if unit == "d": return n * 86_400_000
    return 60_000

if __name__ == "__main__":
    loop()
