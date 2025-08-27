import os, time, json, math, ccxt, datetime as dt
from typing import List, Dict, Any

# ---------- Utilities ----------
DATA_DIR = os.environ.get("DATA_DIR", "/data")
STATE_PATH = os.environ.get("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH = os.environ.get("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))
TRADES_DETAILED_PATH = os.path.join(DATA_DIR, "trades_detailed.json")
CANDLES_WITH_SIGNALS_PATH = os.path.join(DATA_DIR, "candles_with_signals.json")
SNAP_PATH = os.path.join(DATA_DIR, "state_snapshots.json")
BOTCFG_PATH = os.path.join(DATA_DIR, "bot_config.json")

def iso(ts: int) -> str:
    return dt.datetime.utcfromtimestamp(ts/1000).replace(tzinfo=dt.timezone.utc).isoformat()

def atomic_write_json(path: str, obj: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)

def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def append_json_array(path: str, item: Any):
    arr = load_json(path, [])
    arr.append(item)
    atomic_write_json(path, arr)

def ensure_expected_files_exist(state: Dict[str, Any]):
    for p, d in [
        (STATE_PATH, state), (TRADES_PATH, []), (TRADES_DETAILED_PATH, []),
        (CANDLES_WITH_SIGNALS_PATH, []), (SNAP_PATH, []), (BOTCFG_PATH, {})
    ]:
        if not os.path.exists(p):
            atomic_write_json(p, d)

# ---------- Profile loading ----------
def load_profile() -> Dict[str, Any]:
CFG = load_profile()

def get_exchange():
    ex = CFG["EXCHANGE"]
    if ex == "binanceus":
        return ccxt.binanceus({"enableRateLimit": True})
    return getattr(ccxt, ex)({"enableRateLimit": True})

EX = get_exchange()
SYMBOL = CFG["SYMBOL"]
TIMEFRAME = CFG["TIMEFRAME"]

    name = os.environ.get("STRAT_PROFILE") or os.environ.get("PROFILE") or ""
    # Default to embedded env if no profile specified
    profile = {}
    if name:
        profile_dir = os.path.join(os.path.dirname(__file__), "config", "strategies")
        if not os.path.isdir(profile_dir) and os.path.isdir("/config/strategies"):
            profile_dir = "/config/strategies"
        path = os.path.join(profile_dir, f"{name}.json")
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)

    def pick(key, env=None, default=None, co=float):
        if env and env in os.environ:
            return co(os.environ[env]) if co else os.environ[env]
        if key in profile: return profile[key]
        return default

    cfg = {
        # market + timeframe
        "EXCHANGE": pick("EXCHANGE","EXCHANGE","binanceus",str),
        "SYMBOL": pick("SYMBOL","SYMBOL","BTC/USDT",str),
        "TIMEFRAME": pick("TIMEFRAME","TIMEFRAME","1m",str),

        # SMA cross + discipline
        "FAST": int(pick("FAST","FAST",7)),
        "SLOW": int(pick("SLOW","SLOW",25)),
        "CONFIRM_BARS": int(pick("CONFIRM_BARS","CONFIRM_BARS",1)),
        "MIN_HOLD_BARS": int(pick("MIN_HOLD_BARS","MIN_HOLD_BARS",2)),
        "THRESHOLD_PCT": float(pick("THRESHOLD_PCT","THRESHOLD_PCT",0.0003)),

        # costs + friction
        "FEE_RATE": float(pick("FEE_RATE","FEE_RATE",0.001)),
        "SLIPPAGE_BP": float(pick("SLIPPAGE_BP","SLIPPAGE_BP",5)),
        "COST_BUFFER_BP": float(pick("COST_BUFFER_BP","COST_BUFFER_BP",0)),

        # sizing
        "START_CASH_USD": float(pick("START_CASH_USD","START_CASH_USD",200)),
        "ORDER_PCT_EQUITY": (None if os.environ.get("ORDER_PCT_EQUITY") in (None,"","null") else float(os.environ.get("ORDER_PCT_EQUITY")) ) if "ORDER_PCT_EQUITY" in os.environ else (profile.get("ORDER_PCT_EQUITY")),
        "ORDER_SIZE_USD": float(pick("ORDER_SIZE_USD","ORDER_SIZE_USD",20)),
        "MIN_TRADE_USD": float(pick("MIN_TRADE_USD","MIN_TRADE_USD",5)),
        "STACK_FLOOR_USD": float(pick("STACK_FLOOR_USD","STACK_FLOOR_USD",0)),

        # retain policy
        "RETAIN_PCT_UP": float(profile.get("RETAIN_PCT_UP",0.10)),
        "RETAIN_PCT_CHOP": float(profile.get("RETAIN_PCT_CHOP",0.03)),
        "RETAIN_PCT_DOWN": float(profile.get("RETAIN_PCT_DOWN",0.0)),
        "CASH_FLOOR_PCT": float(profile.get("CASH_FLOOR_PCT",0.40)),

        # NEW knobs (fast upgrade)
        "RETAIN_DISABLE_CASH_PCT": float(profile.get("RETAIN_DISABLE_CASH_PCT",0.45)),
        "MIN_RETAIN_USD": float(profile.get("MIN_RETAIN_USD",5.0)),
        "SKIM_PROFIT_PCT": float(profile.get("SKIM_PROFIT_PCT",0.10)),
        "IDLE_CASH_APR": float(profile.get("IDLE_CASH_APR",0.05)),

        # trend slope guard (optional)
        "TREND_SLOPE_BARS": int(profile.get("TREND_SLOPE_BARS",20)),
        "SLOPE_MIN_PCT_PER_BAR": float(profile.get("SLOPE_MIN_PCT_PER_BAR",0.0)),

        # rebalance
        "REBALANCE_DAYS": int(profile.get("REBALANCE_DAYS",30)),
        "REBALANCE_MAX_STASH_PCT": float(profile.get("REBALANCE_MAX_STASH_PCT",0.70)),
        "REBALANCE_TARGET_STASH_PCT": float(profile.get("REBALANCE_TARGET_STASH_PCT",0.60)),
        "PROFILE": name or None,
    }
    return cfg
# ---------- Exchange ----------def tf_ms(tf: str) -> int:
    unit = tf[-1]; n = int(tf[:-1])
    mult = {"s":1000,"m":60000,"h":3600000,"d":86400000}[unit]
    return n*mult

# ---------- Indicators ----------
def sma(vals: List[float], n: int):
    out = [None]*len(vals)
    s=0; q=[]
    for i,v in enumerate(vals):
        q.append(v); s+=v
        if len(q)>n: s-=q.pop(0)
        if len(q)==n: out[i]=s/n
    return out

def slope_pct_per_bar(vals: List[float], bars: int) -> float:
    if len(vals) < bars or vals[-bars] is None or vals[-1] is None: return 0.0
    start = vals[-bars]; end = vals[-1]
    return (end - start) / max(1e-12, start) / bars

# ---------- State ----------
def ensure_state_defaults(state: Dict[str,Any]) -> Dict[str,Any]:
    state.setdefault("start_cash_usd", CFG["START_CASH_USD"])
    state.setdefault("cash_usd", CFG["START_CASH_USD"])
    state.setdefault("trade_coin_units", 0.0)
    state.setdefault("stash_coin_units", 0.0)
    state["coin_units"] = float(state["trade_coin_units"] + state["stash_coin_units"])
    state.setdefault("fees_paid_usd", 0.0)
    state.setdefault("pnl_usd", 0.0)
    state.setdefault("unrealized_pnl_usd", 0.0)
    state.setdefault("position", "flat")
    state.setdefault("entry_price", None)
    state.setdefault("last_action", "hold")
    state.setdefault("last_signal", None)
    state.setdefault("last_rebalance_ts", None)
    state.setdefault("symbol", SYMBOL)
    if CFG["PROFILE"]: state["profile"] = CFG["PROFILE"]
    return state

def reseed_if_missing(state: Dict[str,Any], last_price: float):
    if not state or "cash_usd" not in state:
        state = ensure_state_defaults({})
        state["last_price"] = last_price
        atomic_write_json(STATE_PATH, state)
        ensure_expected_files_exist(state)
    return state, False

# ---------- Sizing helpers ----------
def equity_usd(state: Dict[str,Any], price: float) -> float:
    return float(state["cash_usd"]) + float(state["coin_units"])*price

def order_size_usd(state: Dict[str,Any], price: float) -> float:
    pct = CFG["ORDER_PCT_EQUITY"]
    if pct is not None:
        return max(CFG["MIN_TRADE_USD"], equity_usd(state, price)*pct)
    return max(CFG["MIN_TRADE_USD"], CFG["ORDER_SIZE_USD"])

# ---------- Idle cash APR credit ----------
def apply_idle_cash_yield(state: Dict[str,Any], bars_elapsed: int):
    apr = CFG["IDLE_CASH_APR"]
    if apr <= 0 or bars_elapsed <= 0: return
    # simple per-bar compounding
    per_day = apr/365.0
    per_bar = per_day * (tf_ms(TIMEFRAME)/86400000.0)
    state["cash_usd"] = float(state["cash_usd"]) * (1.0 + per_bar*bars_elapsed)

# ---------- Main loop ----------
def sleep_until_next_close(tfms: int, last_ts: int):
    # sleep until (last_ts + tfms + small buffer)
    now = int(time.time()*1000)
    target = (last_ts // tfms + 1)*tfms + 2000
    if target > now:
        time.sleep((target - now)/1000.0)

def main():
    print(f"[bot] start {CFG['EXCHANGE']}:{SYMBOL} tf={TIMEFRAME} F/S={CFG['FAST']}/{CFG['SLOW']} fee={CFG['FEE_RATE']} profile={CFG.get('PROFILE')}")
    tfms = tf_ms(TIMEFRAME)
    last_processed_ts = None

    while True:
        try:
            # fetch last ~200 candles, CLOSED only
            ohlcv = EX.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
            if not ohlcv or len(ohlcv) < max(CFG["SLOW"]+2, 5):
                time.sleep(2); continue

            # separate closed vs forming
            ts = [c[0] for c in ohlcv]
            last_ts = ts[-1]
            # CCXT returns closed candles; still guard against duplicates
            if last_processed_ts is not None and last_ts == last_processed_ts:
                sleep_until_next_close(tfms, last_ts); continue
            last_processed_ts = last_ts

            closed = ohlcv[:]  # treat as closed
            o = [c[1] for c in closed]; h=[c[2] for c in closed]; l=[c[3] for c in closed]
            c = [c[4] for c in closed]; v=[c[5] for c in closed]
            last_price = float(c[-1])

            # state
            state = load_json(STATE_PATH, {})
            state = ensure_state_defaults(state)
            state, _ = reseed_if_missing(state, last_price)

            # indicators
            fast = sma(c, CFG["FAST"]); slow = sma(c, CFG["SLOW"])
            # confirmations
            def confirmed_up():
                for i in range(1, CFG["CONFIRM_BARS"]+1):
                    if fast[-i] is None or slow[-i] is None or not (fast[-i] > slow[-i]): return False
                return True
            def confirmed_down():
                for i in range(1, CFG["CONFIRM_BARS"]+1):
                    if fast[-i] is None or slow[-i] is None or not (fast[-i] < slow[-i]): return False
                return True

            # hysteresis: skip when near anchor
            anchor = slow[-1] if slow[-1] is not None else last_price
            spread = abs((fast[-1] if fast[-1] is not None else last_price) - anchor) / last_price
            if spread <= CFG["THRESHOLD_PCT"]:
                state["last_action"]="skip"; state["skip_reason"]=f"hysteresis<{CFG['THRESHOLD_PCT']}"
                # snapshot/update and wait next
                state["last_price"]=last_price
                state["unrealized_pnl_usd"]= (last_price - (state.get("entry_price") or last_price))*float(state["trade_coin_units"])
                state["coin_units"] = float(state["trade_coin_units"] + state["stash_coin_units"])
                state["equity_usd"]= equity_usd(state, last_price)
                state["updated_at"]= iso(last_ts)
                atomic_write_json(STATE_PATH, state)
                append_json_array(SNAP_PATH, {"ts": iso(last_ts), "equity_usd": state["equity_usd"]})
                ensure_expected_files_exist(state)

                append_json_array(CANDLES_WITH_SIGNALS_PATH, {
                    "ts": iso(last_ts), "o": o[-1], "h": h[-1], "l": l[-1], "c": c[-1], "v": v[-1],
                    "fast": fast[-1], "slow": slow[-1],
                    "signal": "hold"
                })
                sleep_until_next_close(tfms, last_ts); continue

            # slope/trend filter (optional)
            slope = slope_pct_per_bar(slow, CFG["TREND_SLOPE_BARS"])
            in_uptrend = slope >= CFG["SLOPE_MIN_PCT_PER_BAR"] if CFG["SLOPE_MIN_PCT_PER_BAR"]>0 else True

            # build signal
            signal = "hold"
            if confirmed_up(): signal="buy"
            elif confirmed_down(): signal="sell"

            append_json_array(CANDLES_WITH_SIGNALS_PATH, {
                "ts": iso(last_ts), "o": o[-1], "h": h[-1], "l": l[-1], "c": c[-1], "v": v[-1],
                "fast": fast[-1], "slow": slow[-1],
                "signal": signal
            })

            # per-bar idle cash APR credit
            apply_idle_cash_yield(state, bars_elapsed=1)

            # cooldown by MIN_HOLD_BARS
            # track when last trade closed
            last_trade_close_ts = state.get("last_trade_close_ts")
            if last_trade_close_ts and (last_ts - int(last_trade_close_ts)) < CFG["MIN_HOLD_BARS"]*tfms:
                state["last_action"]="skip"; state["skip_reason"]="cooldown"
                # update bookkeeping
                state["last_price"]=last_price
                state["unrealized_pnl_usd"]= (last_price - (state.get("entry_price") or last_price))*float(state["trade_coin_units"])
                state["coin_units"]= float(state["trade_coin_units"] + state["stash_coin_units"])
                state["equity_usd"]= equity_usd(state, last_price)
                state["updated_at"]= iso(last_ts)
                atomic_write_json(STATE_PATH, state)
                append_json_array(SNAP_PATH, {"ts": iso(last_ts), "equity_usd": state["equity_usd"]})
                ensure_expected_files_exist(state)
                sleep_until_next_close(tfms, last_ts); continue

            # sizing
            trade_usd = order_size_usd(state, last_price)

            # choose retain pct by regime
            retain_pct = 0.0
            if signal == "sell":
                if in_uptrend: retain_pct = CFG["RETAIN_PCT_UP"]
                else: retain_pct = CFG["RETAIN_PCT_CHOP"]  # may be 0.0
            # retain throttle by cash ratio
            cash_ratio = float(state["cash_usd"]) / max(1e-9, equity_usd(state, last_price))
            if cash_ratio < CFG["RETAIN_DISABLE_CASH_PCT"]:
                retain_pct = 0.0

            # execute
            fee_rate = CFG["FEE_RATE"]
            slippage = CFG["SLIPPAGE_BP"]/10000.0

            if signal == "buy":
                if state["cash_usd"] >= CFG["MIN_TRADE_USD"]:
                    qty = (trade_usd / last_price)
                    if qty * last_price < CFG["MIN_TRADE_USD"]:
                        state["last_action"]="skip"; state["skip_reason"]="min_trade"
                    else:
                        # apply fee and slippage
                        fill_price = last_price*(1+slippage)
                        cost = qty*fill_price
                        if cost > state["cash_usd"]:
                            # scale down to available cash
                            qty = state["cash_usd"]/fill_price
                            cost = qty*fill_price
                        fee = cost*fee_rate
                        if cost < CFG["MIN_TRADE_USD"]:
                            state["last_action"]="skip"; state["skip_reason"]="min_trade"
                        else:
                            state["cash_usd"] -= (cost + fee)
                            state["fees_paid_usd"] += fee
                            state["trade_coin_units"] += qty
                            state["position"]="long"; state["entry_price"]=fill_price
                            state["last_action"]="buy"; state["last_signal"]="buy"; state["skip_reason"]=None
                            append_json_array(TRADES_PATH, {
                                "t": iso(last_ts), "type":"buy", "price": fill_price, "units": qty,
                                "fee_usd": round(fee,6), "cash_usd": round(state["cash_usd"],6),
                                "coin_units": round(state["trade_coin_units"]+state["stash_coin_units"],12)
                            })
                            append_json_array(TRADES_DETAILED_PATH, {"t": iso(last_ts), "ev":"buy", "qty":qty, "fill":fill_price})
                            state["last_trade_close_ts"] = last_ts

            elif signal == "sell" and state["trade_coin_units"] > 0:
                qty = state["trade_coin_units"]
                fill_price = last_price*(1-slippage)
                gross = qty*fill_price
                fee = gross*fee_rate
                proceeds = gross - fee
                entry = state.get("entry_price") or fill_price
                realized_pnl = (fill_price - entry)*qty

                # Optional retain to stash (throttled by cash condition above)
                retain_units = 0.0
                if retain_pct > 0.0:
                    # compute retain by pct of what we would sell
                    candidate = qty * retain_pct
                    # enforce MIN_RETAIN_USD
                    if candidate*fill_price < CFG["MIN_RETAIN_USD"]:
                        candidate = 0.0
                    retain_units = min(candidate, qty)

                # execute sell of the rest
                sell_units = max(0.0, qty - retain_units)
                state["trade_coin_units"] -= sell_units
                state["stash_coin_units"] += retain_units
                state["cash_usd"] += (sell_units*fill_price - fee)
                state["fees_paid_usd"] += fee

                # skim some profit back to cash (only if profitable)
                if realized_pnl > 0 and CFG["SKIM_PROFIT_PCT"] > 0:
                    skim = realized_pnl * CFG["SKIM_PROFIT_PCT"]
                    state["cash_usd"] += skim
                    realized_pnl -= skim  # remaining PnL accrues to equity implicitly

                state["position"]="flat"; state["entry_price"]=None
                state["last_action"]="sell"; state["last_signal"]="sell"; state["skip_reason"]=None

                # logs
                if retain_units>0:
                    append_json_array(TRADES_PATH, {
                        "t": iso(last_ts), "type":"retain_to_stash", "price": fill_price, "units": retain_units,
                        "fee_usd": 0.0, "cash_usd": round(state["cash_usd"],6),
                        "coin_units": round(state["trade_coin_units"]+state["stash_coin_units"],12),
                        "note": f"regime={'up' if in_uptrend else 'chop'}, pct={retain_pct:.3f}, min_retain_usd={CFG['MIN_RETAIN_USD']}"
                    })
                append_json_array(TRADES_PATH, {
                    "t": iso(last_ts), "type":"sell", "price": fill_price, "units": -sell_units,
                    "fee_usd": round(fee,6), "cash_usd": round(state["cash_usd"],6),
                    "coin_units": round(state["trade_coin_units"]+state["stash_coin_units"],12),
                    "pnl": round(realized_pnl,6), "note": f"regime={'up' if in_uptrend else 'chop'}"
                })
                append_json_array(TRADES_DETAILED_PATH, {"t": iso(last_ts), "ev":"sell", "qty":sell_units, "fill":fill_price, "retain":retain_units})
                state["pnl_usd"] += realized_pnl
                state["last_trade_close_ts"] = last_ts

            else:
                state["last_action"]="hold"; state["skip_reason"]=None

            # snapshot/update
            state["last_price"]=last_price
            state["coin_units"]= float(state["trade_coin_units"]+state["stash_coin_units"])
            state["unrealized_pnl_usd"]= (last_price - (state.get("entry_price") or last_price))*float(state["trade_coin_units"])
            state["equity_usd"]= equity_usd(state, last_price)
            state["updated_at"]= iso(last_ts)

            # write bot_config mirror (so UI shows active profile values)
            botcfg = {
                "symbol": SYMBOL, "timeframe": TIMEFRAME,
                "fast_sma_len": CFG["FAST"], "slow_sma_len": CFG["SLOW"],
                "confirm_bars": CFG["CONFIRM_BARS"], "min_hold_bars": CFG["MIN_HOLD_BARS"],
                "hysteresis_bp": round(CFG["THRESHOLD_PCT"]*10000, 4),
                "order_size_usd": CFG["ORDER_SIZE_USD"],
                "order_pct_equity": CFG["ORDER_PCT_EQUITY"],
                "maker_fee_bp": CFG["FEE_RATE"]*10000, "taker_fee_bp": CFG["FEE_RATE"]*10000,
                "assumed_slippage_bp": CFG["SLIPPAGE_BP"], "min_notional_usd": 1.0,
                "tick_size": 0.01, "step_size": 1e-5,
                "stack_floor_usd": CFG["STACK_FLOOR_USD"],
                "retain_pct_up": CFG["RETAIN_PCT_UP"], "retain_pct_chop": CFG["RETAIN_PCT_CHOP"], "retain_pct_down": CFG["RETAIN_PCT_DOWN"],
                "cash_floor_pct": CFG["CASH_FLOOR_PCT"],
                "rebalance_days": CFG["REBALANCE_DAYS"],
                "rebalance_max_stash_pct": CFG["REBALANCE_MAX_STASH_PCT"],
                "rebalance_target_stash_pct": CFG["REBALANCE_TARGET_STASH_PCT"],
                "profile": CFG.get("PROFILE"),
                "updated_at": iso(last_ts)
            }
            atomic_write_json(BOTCFG_PATH, botcfg)

            atomic_write_json(STATE_PATH, state)
            append_json_array(SNAP_PATH, {"ts": iso(last_ts), "equity_usd": state["equity_usd"]})
            ensure_expected_files_exist(state)

            sleep_until_next_close(tfms, last_ts)

        except Exception as e:
            print(f"[bot] loop error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
