import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.utils import sma_series


def indicators(closes, fast: int, slow: int, closed_only: bool = True):
    """
    Compute SMAs on CLOSED bars only (drop the last potentially-forming bar).
    """
    seq = list(closes)
    if closed_only and len(seq) > 0:
        seq = seq[:-1]
    f = sma_series(seq, fast)
    s = sma_series(seq, slow)
    return f, s


def decide(
    fast_series,
    slow_series,
    last_price: float,
    cfg,
    last_trade_bar_ts: int,
    bar_ts: int,
    tf_ms: int,
):
    """
    Decision on the LAST CLOSED bar:
      - CONFIRM_BARS: last N CLOSED bars satisfy direction (fast>slow for buy, fast<slow for sell)
      - THRESHOLD_PCT: |fast - slow| / price >= threshold
      - Cooldown: bars_since_last_trade >= MIN_HOLD_BARS
    Returns: (signal: "buy"|"sell"|"none", reason, cooldown_ok: bool, sep)
    """
    k = min(len(fast_series), len(slow_series))
    if k == 0:
        return "none", "", False, 0.0

    def ok_dir(series_fast, series_slow, n, comp):
        n = min(n, k)
        return all(comp(series_fast[-i], series_slow[-i]) for i in range(1, n + 1))

    buy_conf = ok_dir(fast_series, slow_series, cfg.confirm_bars, lambda a, b: a > b)
    sell_conf = ok_dir(fast_series, slow_series, cfg.confirm_bars, lambda a, b: a < b)

    sep = abs(fast_series[-1] - slow_series[-1]) / max(1e-12, last_price)
    threshold_ok = sep >= cfg.threshold_pct

    bars_since = (
        (bar_ts - int(last_trade_bar_ts)) / tf_ms if last_trade_bar_ts else 10**9
    )
    cooldown_ok = bars_since >= cfg.min_hold_bars

    signal, reason = "none", ""
    if buy_conf and threshold_ok:
        signal, reason = "buy", "fast_cross_up"
    elif sell_conf and threshold_ok:
        signal, reason = "sell", "fast_cross_down"

    return signal, reason, cooldown_ok, sep
