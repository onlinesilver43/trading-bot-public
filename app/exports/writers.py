import uuid
from core.utils import iso_from_ms, now_iso
from state.store import save_json, load_json


def write_bot_config(cfg, markets) -> None:
    # best-effort; may be None depending on exchange metadata
    m = markets.get(cfg.symbol, {}) if isinstance(markets, dict) else {}
    tick_size = (m.get("info", {}) or {}).get("tickSize") or (
        m.get("precision", {}) or {}
    ).get("price")
    step_size = (m.get("info", {}) or {}).get("stepSize") or (
        m.get("precision", {}) or {}
    ).get("amount")
    limits = m.get("limits") or {}
    min_notional = (limits.get("cost") or {}).get("min")
    cfg_obj = {
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "fast_sma_len": cfg.fast,
        "slow_sma_len": cfg.slow,
        "confirm_bars": cfg.confirm_bars,
        "hysteresis_bp": cfg.threshold_pct * 10_000.0,
        "order_size_usd": cfg.order_usd,
        "order_pct_equity": None,
        "order_type": "market",
        "maker_fee_bp": cfg.fee_rate * 10_000.0,
        "taker_fee_bp": cfg.fee_rate * 10_000.0,
        "assumed_slippage_bp": 0.0,
        "min_notional_usd": (min_notional if (min_notional is not None) else 0.0),
        "tick_size": tick_size,
        "step_size": step_size,
    }
    save_json(cfg.f_config, cfg_obj, pretty=True)


def write_candles_with_signals(cfg, candles, fast_series, slow_series) -> None:
    opens = [c[1] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]
    vols = [c[5] for c in candles]
    sigs = []
    off_f = len(closes) - len(fast_series)
    off_s = len(closes) - len(slow_series)
    for i in range(len(candles)):
        f = fast_series[i - off_f] if i >= off_f else None
        s = slow_series[i - off_s] if i >= off_s else None
        sig = "flat"
        if (f is not None) and (s is not None):
            if f > s:
                sig = "buy"
            elif f < s:
                sig = "sell"
        sigs.append(
            {
                "ts": iso_from_ms(candles[i][0]),
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i]),
                "volume": float(vols[i]),
                "fast_sma": (
                    None if f is None or i < off_f else float(fast_series[i - off_f])
                ),
                "slow_sma": (
                    None if s is None or i < off_s else float(slow_series[i - off_s])
                ),
                "signal": sig,
            }
        )
    save_json(cfg.f_candles, sigs, pretty=False)


def append_snapshot(cfg, state) -> None:
    snaps = load_json(cfg.f_snap, [])
    snaps.append(
        {
            "ts": now_iso(),
            "symbol": cfg.symbol,
            "timeframe": cfg.timeframe,
            "equity_usd": float(state["equity_usd"]),
            "cash_usd": float(state["cash_usd"]),
            "coin_units": float(state["coin_units"]),
            "realized_pnl_usd": float(state["pnl_usd"]),
            "unrealized_pnl_usd": float(state["unrealized_pnl_usd"]),
            "position_side": state["position"],
            "position_units": float(state["units"]),
            "avg_entry_price": (
                float(state["entry_price"]) if state["entry_price"] else None
            ),
            "last_signal": state["last_signal"],
        }
    )
    if len(snaps) > 5000:
        snaps = snaps[-5000:]
    save_json(cfg.f_snap, snaps, pretty=False)


def append_trades_detailed(cfg, last_buy, sell_info, exit_reason, hold_bars) -> None:
    rows = load_json(cfg.f_trades_det, [])
    rows.append(
        {
            "trade_id": uuid.uuid4().hex[:12],
            "symbol": cfg.symbol,
            "timeframe": cfg.timeframe,
            "ts_open": last_buy["ts_open"],
            "ts_close": now_iso(),
            "side": "long",
            "qty_asset": sell_info["units"],
            "entry_price": float(last_buy["entry_price"]),
            "exit_price": float(sell_info["exit_price"]),
            "notional_entry_usd": float(last_buy["entry_price"]) * sell_info["units"],
            "notional_exit_usd": float(sell_info["exit_price"]) * sell_info["units"],
            "fee_entry_usd": float(last_buy["fee_usd"]),
            "fee_exit_usd": float(sell_info["fee"]),
            "pnl_usd_gross": float(sell_info["pnl_gross"]),
            "pnl_usd_net": float(sell_info["pnl_net"]),
            "hold_bars": int(hold_bars),
            "entry_reason": str(last_buy.get("entry_reason", "signal_flip")),
            "exit_reason": exit_reason or "signal_flip",
        }
    )
    save_json(cfg.f_trades_det, rows[-2000:], pretty=True)
