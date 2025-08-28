from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def tf_to_ms(tf: str) -> int:
    n = int("".join([c for c in tf if c.isdigit()]) or "1")
    unit = "".join([c for c in tf if c.isalpha()]).lower()
    return {"m": 60_000, "h": 3_600_000, "d": 86_400_000}.get(unit, 60_000) * n


def sma_series(vals, n: int):
    if n <= 0 or len(vals) < n:
        return []
    out = []
    s = sum(vals[:n])
    out.append(s / n)
    for i in range(n, len(vals)):
        s += vals[i] - vals[i - n]
        out.append(s / n)
    return out
