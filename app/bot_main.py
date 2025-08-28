import os
import time
from app.core.config import Config
from app.core.utils import now_iso, tf_to_ms
from app.state.store import load_json, save_json, ensure_defaults
from app.exchange.ccxt_client import Client
from app.strategy.sma_crossover import indicators, decide
from app.portfolio.paper import buy as pw_buy, sell as pw_sell
from app.exports.writers import (
    write_bot_config,
    write_candles_with_signals,
    append_trades_detailed,
)


def main():
    cfg = Config()
    api_key = os.getenv("BINANCE_API_KEY") or os.getenv("API_KEY")
    api_sec = os.getenv("BINANCE_API_SECRET") or os.getenv("API_SECRET")
    ex = Client(cfg.exchange, api_key, api_sec)

    state = ensure_defaults(load_json(cfg.state_path, {}), cfg)
    trades = load_json(cfg.trades_path, [])
    markets = ex.load_markets()
    write_bot_config(cfg, markets)

    tfms = tf_to_ms(cfg.timeframe)
    last_buy = None

    print(
        f"[bot] start {cfg.exchange}:{cfg.symbol} tf={cfg.timeframe} F/S={cfg.fast}/{cfg.slow} fee={cfg.fee_rate} "
        f"rules: confirm={cfg.confirm_bars} hold={cfg.min_hold_bars} thr={cfg.threshold_pct} minT={cfg.min_trade_usd}",
        flush=True,
    )

    while True:
        try:
            candles = ex.fetch_ohlcv(cfg.symbol, timeframe=cfg.timeframe, limit=200)
            if not candles or len(candles) < max(cfg.fast, cfg.slow) + cfg.confirm_bars:
                time.sleep(cfg.loop_sec)
                continue

            closes = [c[4] for c in candles]
            last_ts = candles[-1][0]
            last = float(closes[-1])

            f_series, s_series = indicators(closes, cfg.fast, cfg.slow)
            write_candles_with_signals(cfg, candles, f_series, s_series)

            # mark-to-market
            state["last_price"] = last
            state["equity_usd"] = (
                float(state["cash_usd"]) + float(state["coin_units"]) * last
            )
            if state["position"] == "long" and state["entry_price"] is not None:
                est_exit = last * (1.0 - cfg.fee_rate)
                est_entry = float(state["entry_price"]) * (1.0 + cfg.fee_rate)
                state["unrealized_pnl_usd"] = (est_exit - est_entry) * float(
                    state["units"]
                )
            else:
                state["unrealized_pnl_usd"] = 0.0

            # decision
            signal, reason, cooldown_ok, _sep = decide(
                f_series,
                s_series,
                last,
                cfg,
                state.get("last_trade_bar_ts", 0),
                last_ts,
                tfms,
            )
            state["skip_reason"] = ""
            entry_reason = reason if signal == "buy" else None
            exit_reason = reason if signal == "sell" else None

            # BUY
            if signal == "buy" and state["position"] != "long":
                if not cooldown_ok:
                    state["skip_reason"] = f"cooldown < {cfg.min_hold_bars} bars"
                else:
                    spend = min(cfg.order_usd, state["cash_usd"])
                    if spend < cfg.min_trade_usd:
                        state["skip_reason"] = f"min_trade ${cfg.min_trade_usd}"
                    else:
                        res = pw_buy(state, last, spend, cfg.fee_rate)
                        if res["ok"]:
                            state["last_trade_bar_ts"] = last_ts
                            last_buy = {
                                "ts_open": now_iso(),
                                "entry_price": last,
                                "qty": res["units"],
                                "fee_usd": res["fee"],
                                "entry_reason": entry_reason or "signal_flip",
                                "bar_ts": last_ts,
                            }
                            trades.append(
                                {
                                    "t": now_iso(),
                                    "type": "buy",
                                    "price": last,
                                    "units": res["units"],
                                    "fee_usd": res["fee"],
                                    "cash_usd": state["cash_usd"],
                                    "coin_units": state["coin_units"],
                                }
                            )

            # SELL
            elif signal == "sell" and state["position"] == "long":
                if not cooldown_ok:
                    state["skip_reason"] = f"cooldown < {cfg.min_hold_bars} bars"
                else:
                    res = pw_sell(state, last, cfg.fee_rate)
                    if res["ok"]:
                        state["last_trade_bar_ts"] = last_ts
                        trades.append(
                            {
                                "t": now_iso(),
                                "type": "sell",
                                "price": last,
                                "units": res["units"],
                                "fee_usd": res["fee"],
                                "pnl": res["pnl_net"],
                                "cash_usd": state["cash_usd"],
                                "coin_units": state["coin_units"],
                            }
                        )
                        # detailed round-trip
                        if last_buy:
                            hold_bars = int(
                                round(
                                    (last_ts - last_buy.get("bar_ts", last_ts)) / tfms
                                )
                            )
                            append_trades_detailed(
                                cfg,
                                last_buy,
                                {
                                    "units": res["units"],
                                    "fee": res["fee"],
                                    "exit_price": last,
                                    "pnl_gross": res["pnl_gross"],
                                    "pnl_net": res["pnl_net"],
                                },
                                exit_reason,
                                hold_bars,
                            )
                        last_buy = None

            # snapshot + persist
            from app.exports.writers import append_snapshot as _append_snapshot

            _append_snapshot(cfg, state)

            state["updated_at"] = now_iso()
            save_json(cfg.state_path, state, pretty=True)
            save_json(cfg.trades_path, trades[-500:], pretty=True)

        except Exception as e:
            print(f"[bot] error: {e}", flush=True)

        time.sleep(cfg.loop_sec)


if __name__ == "__main__":
    main()
