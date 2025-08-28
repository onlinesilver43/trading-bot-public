import ccxt


class Client:
    def __init__(self, exchange_name: str, api_key=None, api_secret=None):
        params = {"enableRateLimit": True}
        if api_key and api_secret:
            params.update({"apiKey": api_key, "secret": api_secret})
        self.ccxt = getattr(ccxt, exchange_name)(params)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200):
        return self.ccxt.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def load_markets(self):
        try:
            return self.ccxt.load_markets()
        except Exception:
            return {}
