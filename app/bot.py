last_snapshot_ts = 0
import os, time, json, uuid
from datetime import datetime, timezone
import ccxt

# --- Params (env) ---
EXCHANGE  = os.getenv("EXCHANGE", "binanceus")
SYMBOL    = os.getenv("SYMBOL", "BTC/USDT")     # on Binance.US you can also use BTC/USD
TIMEFRAME = os.getenv("TIMEFRAME", "5m")
FAST      = int(os.getenv("FAST", "7"))
SLOW      = int(os.getenv("SLOW", "25"))
ORDER_USD = float(os.getenv("ORDER_SIZE_USD", "50"))
LOOP_SEC  = int(os.getenv("LOOP_SECONDS", "20"))

# Paper wallet
START_CASH_USD   = float(os.getenv("START_CASH_USD", "10000"))
START_COIN_UNITS = float(os.getenv("START_COIN_UNITS", "0"))
FEE_RATE         = float(os.getenv("FEE_RATE", "0.001"))  # 0.1%

# Guardrails
CONFIRM_BARS   = int(os.getenv("CONFIRM_BARS", "3"))
MIN_HOLD_BARS  = int(os.getenv("MIN_HOLD_BARS", "5"))
THRESHOLD_PCT  = float(os.getenv("THRESHOLD_PCT", "0.001"))   # 0.1%
MIN_TRADE_USD  = float(os.getenv("MIN_TRADE_USD", "20"))

# Files (keep original paper_* and add new ones)
STATE_PATH   = os.getenv("STATE_PATH", "/data/paper_state.json")
TRADES_PATH  = os.getenv("TRADES_PATH", "/data/paper_trades.json")
DATA_DIR     = os.path.dirname(STATE_PATH) or "/data"
F_TRADES_DET = os.path.join(DATA_DIR, "trades_detailed.json")
F_CANDLES    = os.path.join(DATA_DIR, "candles_with_signals.json")
F_CONFIG     = os.path.join(DATA_DIR, "bot_config.json")
F_SNAP       = os.path.join(DATA_DIR, "state_snapshots.json")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def iso_from_ms(ms):
    return datetime.fromtimestamp(ms/1000, tz=timezone.utc).isoformat()

def load_json(path, default):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception:
        return default

def save_json(path, obj, pretty=False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2 if pretty else None)
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
    n = int(''.join([c for c in tf if c.isdigit()]) or "1")
    unit = ''.join([c for c in tf if c.isalpha()]).lower()
    return {"m":60_000,"h":3_600_000,"d":86_400_000}.get(unit,60_000)*n

def ensure_defaults(state):
    defaults = {
        "symbol": SYMBOL, "timeframe": TIMEFRAME,
        "position": "flat", "entry_price": None, "units": 0.0,
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
    state["rules"] = defaults["rules"]
    return state

def write_bot_config(exchange):
    # best-effort tick/step sizes (may be None if symbol not found)
    tick_size = None; step_size = None; min_notional = None
    try:
        markets = exchange.load_markets()
        m = markets.get(SYMBOL) or {}
        prec = m.get("precision") or {}
        tick_size = m.get("info",{}).get("tickSize") or prec.get("price")
        step_size = m.get("info",{}).get("stepSize") or prec.get("amount")
        limits = m.get("limits") or {}
        min_notional = (limits.get("cost") or {}).get("min")
    except Exception:
        pass

    cfg = {
        "symbol": SYMBOL, "timeframe": TIMEFRAME,
        "fast_sma_len": FAST, "slow_sma_len": SLOW,
        "confirm_bars": CONFIRM_BARS,
        "hysteresis_bp": THRESHOLD_PCT * 10_000.0,
        "order_size_usd": ORDER_USD,
        "order_pct_equity": None,
        "order_type": "market",
        "maker_fee_bp": FEE_RATE * 10_000.0,
        "taker_fee_bp": FEE_RATE * 10_000.0,
        "assumed_slippage_bp": 0.0,
        "min_notional_usd": min_notional if (min_notional is not None) else 0.0,
        "tick_size": tick_size, "step_size": step_size
    }
    save_json(F_CONFIG, cfg, pretty=True)

def main():
    exchange_class = getattr(ccxt, EXCHANGE)
    ex = exchange_class({"enableRateLimit": True})

    state = ensure_defaults(load_json(STATE_PATH, {}))
    trades = load_json(TRADES_PATH, [])
    trades_det = load_json(F_TRADES_DET, [])
    snapshots = load_json(F_SNAP, [])
    tfms = tf_to_ms(TIMEFRAME)

    write_bot_config(ex)
    print(f"[bot] start {EXCHANGE}:{SYMBOL} tf={TIMEFRAME} F/S={FAST}/{SLOW} fee={FEE_RATE}", flush=True)

    last_buy = None

    while True:
        try:
            candles = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
        candles_closed, last_closed_ts = _drop_forming(candles)  # [ts, o,h,l,c,v]
            if not candles or len(candles) < max(FAST, SLOW) + CONFIRM_BARS:
                time.sleep(LOOP_SEC); continue

            opens  = [c[1] for c in candles]
            highs  = [c[2] for c in candles]
            lows   = [c[3] for c in candles]
            closes = [c[4] for c in candles]
            vols   = [c[5] for c in candles]
            last_ts = candles[-1][0]
            last = closes[-1]

            fast_series = sma_series(closes, FAST)
            slow_series = sma_series(closes, SLOW)
            k = min(len(fast_series), len(slow_series))
            if k < CONFIRM_BARS:
                time.sleep(LOOP_SEC); continue

            # snapshot mark-to-market
            state["last_price"] = last
            equity = float(state["cash_usd"]) + float(state["coin_units"]) * last
            state["equity_usd"] = equity
            if state["position"] == "long" and state["entry_price"] is not None:
                est_exit = last * (1.0 - FEE_RATE)
                est_entry = float(state["entry_price"]) * (1.0 + FEE_RATE)
                state["unrealized_pnl_usd"] = (est_exit - est_entry) * float(state["units"])
            else:
                state["unrealized_pnl_usd"] = 0.0

            # build candles_with_signals.json (for the whole window)
            sigs = []
            # align smas to closes tail
            off_fast = len(closes) - len(fast_series)
            off_slow = len(closes) - len(slow_series)
            for i in range(len(candles)):
                f = fast_series[i - off_fast] if i >= off_fast else None
                s = slow_series[i - off_slow] if i >= off_slow else None
                sig = "flat"
                if (f is not None) and (s is not None):
                    if f > s: sig = "buy"
                    elif f < s: sig = "sell"
                sigs.append({
                    "ts": iso_from_ms(candles[i][0]),
                    "open": float(opens[i]), "high": float(highs[i]), "low": float(lows[i]), "close": float(closes[i]),
                    "volume": float(vols[i]),
                    "fast_sma": (None if f is None or i < off_fast else float(fast_series[i - off_fast])),
                    "slow_sma": (None if s is None or i < off_slow else float(slow_series[i - off_slow])),
                    "signal": sig
                })
            # write candles_with_signals (minified is fine)
            save_json(F_CANDLES, sigs, pretty=False)

            # guardrails
            buy_conf  = all(fast_series[-i] > slow_series[-i] for i in range(1, CONFIRM_BARS+1))
            sell_conf = all(fast_series[-i] < slow_series[-i] for i in range(1, CONFIRM_BARS+1))
            sep = abs(fast_series[-1] - slow_series[-1]) / last
            threshold_ok = sep >= THRESHOLD_PCT
            bars_since_flip = (last_ts - int(state.get("last_trade_bar_ts", 0))) / tfms if state.get("last_trade_bar_ts", 0) else 1e9
            cooldown_ok = bars_since_flip >= MIN_HOLD_BARS

            # decision
            state["skip_reason"] = ""
            entry_reason = "fast_cross_up" if buy_conf else None
            exit_reason  = "fast_cross_down" if sell_conf else None
            signal = "none"
            if buy_conf and threshold_ok: signal = "buy"
            elif sell_conf and threshold_ok: signal = "sell"

            # BUY
            if signal == "buy" and state["position"] != "long":
                if not cooldown_ok:
                    state["skip_reason"] = f"cooldown {bars_since_flip:.1f} < {MIN_HOLD_BARS} bars"
                else:
                    spend = min(ORDER_USD, state["cash_usd"])
                    if spend < MIN_TRADE_USD:
                        state["skip_reason"] = f"min_trade ${MIN_TRADE_USD}"
                    else:
                        units_afford = state["cash_usd"] / (last * (1.0 + FEE_RATE))
                        units_target = spend / last
                        units = max(0.0, min(units_target, units_afford))
                        if units > 0:
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
                            last_buy = {
                                "ts_open": now_iso(), "entry_price": last, "qty": units,
                                "fee_entry_usd": fee_buy, "entry_reason": entry_reason or "signal_flip",
                                "bar_ts": last_ts
                            }
                            trades.append({
                                "t": now_iso(), "type": "buy", "price": last, "units": units,
                                "fee_usd": fee_buy, "cash_usd": state["cash_usd"], "coin_units": state["coin_units"]
                            })

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
                        pnl_gross = (last - float(state["entry_price"])) * units
                        pnl_net   = (last * (1.0 - FEE_RATE) - float(state["entry_price"]) * (1.0 + FEE_RATE)) * units
                        state["pnl_usd"] = float(state["pnl_usd"]) + pnl_net
                        state["fees_paid_usd"] += fee_sell
                        state["position"] = "flat"
                        state["entry_price"] = None
                        state["units"] = 0.0
                        state["last_signal"] = "sell"
                        state["last_action"] = f"SELL {units:.8f} (pnl {pnl_net:.2f})"
                        state["last_trade_bar_ts"] = last_ts
                        trades.append({
                            "t": now_iso(), "type": "sell", "price": last, "units": units,
                            "fee_usd": fee_sell, "pnl": pnl_net, "cash_usd": state["cash_usd"], "coin_units": state["coin_units"]
                        })
                        # ---- trades_detailed round-trip ----
                        if last_buy:
                            trade_id = uuid.uuid4().hex[:12]
                            hold_bars = int(round((last_ts - last_buy.get("bar_ts", last_ts)) / tf_to_ms(TIMEFRAME)))
                            det = {
                                "trade_id": trade_id,
                                "symbol": SYMBOL, "timeframe": TIMEFRAME,
                                "ts_open": last_buy["ts_open"], "ts_close": now_iso(),
                                "side": "long",
                                "qty_asset": units,
                                "entry_price": float(last_buy["entry_price"]),
                                "exit_price": float(last),
                                "notional_entry_usd": float(last_buy["entry_price"]) * units,
                                "notional_exit_usd": float(last) * units,
                                "fee_entry_usd": float(last_buy["fee_entry_usd"]),
                                "fee_exit_usd": float(fee_sell),
                                "pnl_usd_gross": float(pnl_gross),
                                "pnl_usd_net": float(pnl_net),
                                "hold_bars": hold_bars,
                                "entry_reason": str(last_buy.get("entry_reason","signal_flip")),
                                "exit_reason": exit_reason or "signal_flip"
                            }
                            trades_det.append(det)
                            save_json(F_TRADES_DET, trades_det[-2000:], pretty=True)
                        last_buy = None

            # append snapshot each evaluation (keeps last 5000)
            snapshots.append({
                "ts": now_iso(),
                "symbol": SYMBOL, "timeframe": TIMEFRAME,
                "equity_usd": float(state["equity_usd"]),
                "cash_usd": float(state["cash_usd"]),
                "coin_units": float(state["coin_units"]),
                "realized_pnl_usd": float(state["pnl_usd"]),
                "unrealized_pnl_usd": float(state["unrealized_pnl_usd"]),
                "position_side": state["position"],
                "position_units": float(state["units"]),
                "avg_entry_price": (float(state["entry_price"]) if state["entry_price"] else None),
                "last_signal": state["last_signal"]
            })
            if len(snapshots) > 5000: snapshots = snapshots[-5000:]
            # append once per closed bar
            if last_closed_ts != last_snapshot_ts:
                last_snapshot_ts = last_closed_ts
                save_json(F_SNAP, snapshots, pretty=False)

            # Save originals
            state["updated_at"] = now_iso()
            save_json(STATE_PATH, state, pretty=True)
            save_json(TRADES_PATH, trades[-500:], pretty=True)

        except Exception as e:
            print(f"[bot] error: {e}", flush=True)

        time.sleep(LOOP_SEC)

if __name__ == "__main__":
    main()

def _drop_forming(candles):
    """
    Given CCXT ohlcv list [[ms,o,h,l,c,v],...], return (closed, last_closed_ts).
    Drops the last potentially-forming bar.
    """
    if not candles or len(candles) < 2:
        return (candles or []), (candles[-1][0] if candles else 0)
    closed = candles[:-1]
    return closed, closed[-1][0]
