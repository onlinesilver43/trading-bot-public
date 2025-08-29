import json
import os
from typing import Any
from core.utils import now_iso


def load_json(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str, obj: Any, pretty: bool = False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2 if pretty else None)
    os.replace(tmp, path)


def ensure_defaults(state: dict, cfg) -> dict:
    defaults = {
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "position": "flat",
        "entry_price": None,
        "units": 0.0,
        "last_signal": "none",
        "pnl_usd": 0.0,
        "fees_paid_usd": 0.0,
        "start_cash_usd": cfg.start_cash_usd,
        "start_coin_units": cfg.start_coin_units,
        "cash_usd": cfg.start_cash_usd,
        "coin_units": cfg.start_coin_units,
        "last_price": None,
        "equity_usd": cfg.start_cash_usd,
        "unrealized_pnl_usd": 0.0,
        "last_action": "init",
        "skip_reason": "",
        "last_trade_bar_ts": 0,
        "updated_at": now_iso(),
        "rules": {
            "CONFIRM_BARS": cfg.confirm_bars,
            "MIN_HOLD_BARS": cfg.min_hold_bars,
            "THRESHOLD_PCT": cfg.threshold_pct,
            "MIN_TRADE_USD": cfg.min_trade_usd,
            "FAST": cfg.fast,
            "SLOW": cfg.slow,
            "FEE_RATE": cfg.fee_rate,
        },
    }
    for k, v in defaults.items():
        if k not in state:
            state[k] = v
    state["rules"] = defaults["rules"]
    return state
