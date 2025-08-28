import os


def _desired_usd(state: dict, price: float, default_usd: float) -> float:
    """
    If ORDER_PCT_EQUITY is set, spend equity * pct; else use default_usd.
    """
    try:
        pct = float(os.getenv("ORDER_PCT_EQUITY", "").strip() or "0")
    except Exception:
        pct = 0.0
    if pct > 0:
        equity = float(state.get("cash_usd", 0.0)) + float(
            state.get("coin_units", 0.0)
        ) * float(price)
        return max(0.0, equity * pct)
    return float(default_usd)


def can_spend(
    cash_usd: float, fee_rate: float, price: float, desired_usd: float
) -> float:
    """Units you can buy, respecting fees and cash."""
    spend = min(desired_usd, cash_usd)
    units_afford = cash_usd / (price * (1.0 + fee_rate))
    units_target = spend / price
    return max(0.0, min(units_target, units_afford))


def buy(state: dict, price: float, usd_amount: float, fee_rate: float) -> dict:
    usd_amount = _desired_usd(state, price, usd_amount)
    units = can_spend(state["cash_usd"], fee_rate, price, usd_amount)
    if units <= 0:
        return {"ok": False, "reason": "insufficient cash"}
    fee = units * price * fee_rate
    cost = units * price + fee
    state["cash_usd"] = float(state["cash_usd"]) - float(cost)
    state["coin_units"] = float(state["coin_units"]) + float(units)
    state["position"] = "long"
    state["entry_price"] = float(price)
    state["units"] = float(units)
    state["fees_paid_usd"] = float(state.get("fees_paid_usd", 0.0)) + float(fee)
    state["last_signal"] = "buy"
    state["last_action"] = f"BUY {units:.8f}"
    return {"ok": True, "units": units, "fee": fee, "cost": cost, "entry_price": price}


def sell(state: dict, price: float, fee_rate: float) -> dict:
    units = float(state.get("units") or state.get("coin_units") or 0.0)
    if units <= 0:
        return {"ok": False, "reason": "flat"}
    fee = units * price * fee_rate
    proceeds = units * price - fee
    pnl_net = (
        price * (1.0 - fee_rate) - float(state["entry_price"]) * (1.0 + fee_rate)
    ) * units
    pnl_gross = (price - float(state["entry_price"])) * units
    state["cash_usd"] = float(state["cash_usd"]) + float(proceeds)
    state["coin_units"] = float(state["coin_units"]) - float(units)
    state["pnl_usd"] = float(state.get("pnl_usd", 0.0)) + float(pnl_net)
    state["fees_paid_usd"] = float(state.get("fees_paid_usd", 0.0)) + float(fee)
    state["position"] = "flat"
    state["entry_price"] = None
    state["units"] = 0.0
    state["last_signal"] = "sell"
    state["last_action"] = f"SELL {units:.8f} (pnl {pnl_net:.2f})"
    return {
        "ok": True,
        "units": units,
        "fee": fee,
        "proceeds": proceeds,
        "pnl_gross": pnl_gross,
        "pnl_net": pnl_net,
        "exit_price": price,
    }
