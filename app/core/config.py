import os
from dataclasses import dataclass

@dataclass
class Config:
    exchange: str = os.getenv("EXCHANGE", "binanceus")
    symbol: str = os.getenv("SYMBOL", "BTC/USDT")
    timeframe: str = os.getenv("TIMEFRAME", "5m")
    fast: int = int(os.getenv("FAST", "7"))
    slow: int = int(os.getenv("SLOW", "25"))
    order_usd: float = float(os.getenv("ORDER_SIZE_USD", "50"))
    loop_sec: int = int(os.getenv("LOOP_SECONDS", "20"))

    start_cash_usd: float = float(os.getenv("START_CASH_USD", "10000"))
    start_coin_units: float = float(os.getenv("START_COIN_UNITS", "0"))
    fee_rate: float = float(os.getenv("FEE_RATE", "0.001"))

    confirm_bars: int = int(os.getenv("CONFIRM_BARS", "3"))
    min_hold_bars: int = int(os.getenv("MIN_HOLD_BARS", "5"))
    threshold_pct: float = float(os.getenv("THRESHOLD_PCT", "0.001"))
    min_trade_usd: float = float(os.getenv("MIN_TRADE_USD", "20"))

    state_path: str = os.getenv("STATE_PATH", "/data/paper_state.json")
    trades_path: str = os.getenv("TRADES_PATH", "/data/paper_trades.json")

    @property
    def data_dir(self) -> str:
        import os
        return os.path.dirname(self.state_path) or "/data"

    # derived export files
    @property
    def f_trades_det(self): return f"{self.data_dir}/trades_detailed.json"
    @property
    def f_candles(self):    return f"{self.data_dir}/candles_with_signals.json"
    @property
    def f_config(self):     return f"{self.data_dir}/bot_config.json"
    @property
    def f_snap(self):       return f"{self.data_dir}/state_snapshots.json"
