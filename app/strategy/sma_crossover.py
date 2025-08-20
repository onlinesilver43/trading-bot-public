from app.core.utils import sma_series

def indicators(closes, fast: int, slow: int):
    f = sma_series(closes, fast)
    s = sma_series(closes, slow)
    return f, s

def decide(fast_series, slow_series, last_price: float, cfg, last_trade_bar_ts: int, bar_ts: int, tf_ms: int):
    k = min(len(fast_series), len(slow_series))
    if k == 0: 
        return "none", "", False, 0.0

    buy_conf  = all(fast_series[-i] > slow_series[-i] for i in range(1, cfg.confirm_bars+1))
    sell_conf = all(fast_series[-i] < slow_series[-i] for i in range(1, cfg.confirm_bars+1))
    sep = abs(fast_series[-1] - slow_series[-1]) / max(1e-12, last_price)
    threshold_ok = sep >= cfg.threshold_pct

    bars_since = (bar_ts - int(last_trade_bar_ts)) / tf_ms if last_trade_bar_ts else 1e9
    cooldown_ok = bars_since >= cfg.min_hold_bars

    signal = "none"
    reason = ""
    if buy_conf and threshold_ok: signal, reason = "buy", "fast_cross_up"
    elif sell_conf and threshold_ok: signal, reason = "sell", "fast_cross_down"

    return signal, reason, cooldown_ok, sep
