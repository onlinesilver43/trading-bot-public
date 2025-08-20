import json, os
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse

STATE_PATH  = os.getenv("STATE_PATH", "/data/paper_state.json")
TRADES_PATH = os.getenv("TRADES_PATH", "/data/paper_trades.json")

app = FastAPI()

def load(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

@app.get("/", response_class=HTMLResponse)
def home():
    s = load(STATE_PATH, {})
    t = load(TRADES_PATH, [])
    last_trades = t[-10:][::-1]
    html = f"""
    <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Trading Bots – Status</title>
    <style>
      body {{ font-family: system-ui, Arial; margin: 24px; max-width: 900px; }}
      h1 {{ margin: 0 0 8px; }}
      .grid {{ display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; }}
      .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 16px; }}
      table {{ width:100%; border-collapse: collapse; }}
      th, td {{ border-bottom:1px solid #eee; padding: 8px; text-align:left; }}
      .pnl {{ font-weight: 700; }}
    </style>
    </head><body>
      <h1>Trading Bots – Status</h1>
      <p>Updated: <b>{s.get('updated_at','—')}</b></p>
      <div class="grid">
        <div class="card">
          <h3>Bot</h3>
          <p>Symbol: <b>{s.get('symbol','')}</b></p>
          <p>Position: <b>{s.get('position','')}</b> @ {s.get('entry_price','—')}</p>
          <p class="pnl">Total PnL (paper): ${float(s.get('pnl_usd',0.0)):.2f}</p>
        </div>
        <div class="card">
          <h3>Recent Trades</h3>
          <table>
            <tr><th>Time (UTC)</th><th>Type</th><th>Price</th><th>Units</th><th>PnL</th></tr>
            {''.join(f"<tr><td>{x.get('t','')}</td><td>{x.get('type','')}</td><td>{x.get('price','')}</td><td>{x.get('units','')}</td><td>{x.get('pnl','')}</td></tr>" for x in last_trades)}
          </table>
        </div>
      </div>
      <p><a href="/api/state">/api/state</a></p>
    </body></html>
    """
    return HTMLResponse(content=html, status_code=200)

@app.get("/api/state", response_class=JSONResponse)
def api_state():
    s = load(STATE_PATH, {})
    t = load(TRADES_PATH, [])
    return JSONResponse({"state": s, "trades": t[-100:]})
