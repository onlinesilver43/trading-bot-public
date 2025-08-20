def can_spend(cash_usd: float, fee_rate: float, price: float, desired_usd: float) -> float:
    """Returns units you can buy, respecting fees and cash."""
    spend = min(desired_usd, cash_usd)
    units_afford = cash_usd / (price * (1.0 + fee_rate))
    units_target = spend / price
    return max(0.0, min(units_target, units_afford))

def buy(state: dict, price: float, usd_amount: float, fee_rate: float) -> dict:
    units = can_spend(state["cash_usd"], fee_rate, price, usd_amount)
    if units <= 0: 
        return {"ok": False, "reason": "insufficient cash"}
    fee = units * price * fee_rate
    cost = units * price + fee
    state["cash_usd"]  -= cost
    state["coin_units"] += units
    state["position"]   = "long"
    state["entry_price"]= price
    state["units"]      = units
    state["fees_paid_usd"] += fee
    state["last_signal"] = "buy"
    state["last_action"] = f"BUY {units:.8f}"
    return {"ok": True, "units": units, "fee": fee, "cost": cost}

def sell(state: dict, price: float, fee_rate: float) -> dict:
    units = float(state.get("units", 0.0))
    if units <= 0: 
        return {"ok": False, "reason": "no position"}
    fee = units * price * fee_rate
    proceeds = units * price - fee
    state["cash_usd"]  += proceeds
    state["coin_units"]-= units
    pnl_net = (price * (1.0 - fee_rate) - float(state["entry_price"]) * (1.0 + fee_rate)) * units
    pnl_gross = (price - float(state["entry_price"])) * units
    state["pnl_usd"] = float(state["pnl_usd"]) + pnl_net
    state["fees_paid_usd"] += fee
    state["position"] = "flat"
    state["entry_price"]= None
    state["units"]      = 0.0
    state["last_signal"] = "sell"
    state["last_action"] = f"SELL {units:.8f} (pnl {pnl_net:.2f})"
    return {"ok": True, "units": units, "fee": fee, "proceeds": proceeds, "pnl_gross": pnl_gross, "pnl_net": pnl_net}
