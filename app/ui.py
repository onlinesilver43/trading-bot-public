import json, os, math
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

STATE_PATH  = os.getenv("STATE_PATH", "/data/paper_state.json")
TRADES_PATH = os.getenv("TRADES_PATH", "/data/paper_trades.json")

app = FastAPI()

def load(path, default):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception: return default

@app.get("/", response_class=HTMLResponse)
def home():
    # Static shell; data is filled by JS via /api/state every 2s
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Trading Bots – Status</title>
  <style>
    :root { --bg:#0b1020; --card:#141a2d; --text:#e8ecff; --muted:#9aa4c7; --accent:#6ea8fe; --green:#41d1a7; --red:#ff6b6b; }
    *{box-sizing:border-box;}
    body { margin:0; padding:24px; font: 15px/1.5 system-ui, -apple-system, Segoe UI, Roboto, Arial; background:var(--bg); color:var(--text);}
    h1 { margin:0 0 16px; font-size:28px; }
    .grid { display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(260px,1fr)); }
    .card { background:var(--card); border-radius:16px; padding:16px; box-shadow:0 6px 24px rgba(0,0,0,.25); }
    .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
    .value { font-weight:700; font-size:20px; }
    .row { display:flex; justify-content:space-between; gap:12px; margin:8px 0; }
    table { width:100%; border-collapse:collapse; }
    th,td { padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.06); text-align:left; }
    th { color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
    .pnl-pos { color:var(--green); }
    .pnl-neg { color:var(--red); }
    a { color:var(--accent); }
    .muted { color:var(--muted); }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; background:rgba(255,255,255,.08); font-size:12px; }
  </style>
</head>
<body>
  <h1>Trading Bots – Status <span class="muted" id="updated"></span></h1>
  <div class="grid">
    <div class="card">
      <div class="row"><div class="label">Symbol</div><div class="value" id="symbol">—</div></div>
      <div class="row"><div class="label">Position</div><div class="value" id="position">—</div></div>
      <div class="row"><div class="label">Last price</div><div class="value" id="last_price">—</div></div>
      <div class="row"><div class="label">Fast/Slow</div><div class="value" id="faslow" class="muted">SMA</div></div>
    </div>

    <div class="card">
      <div class="label">Starting</div>
      <div class="row"><div>Cash (USD)</div><div class="value" id="start_cash">—</div></div>
      <div class="row"><div>Coin (units)</div><div class="value" id="start_coin">—</div></div>
    </div>

    <div class="card">
      <div class="label">Current</div>
      <div class="row"><div>Cash (USD)</div><div class="value" id="cash">—</div></div>
      <div class="row"><div>Coin (units)</div><div class="value" id="coin">—</div></div>
      <div class="row"><div>Equity (USD)</div><div class="value" id="equity">—</div></div>
    </div>

    <div class="card">
      <div class="label">PnL</div>
      <div class="row"><div>Total PnL (USD)</div><div class="value" id="pnl">—</div></div>
      <div class="row"><div>Fees paid (USD)</div><div class="value" id="fees">—</div></div>
      <div class="row"><div>Last signal</div><div class="value pill" id="signal">—</div></div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <div class="row"><div class="label">Recent Trades</div><div class="muted" id="tradeCount"></div></div>
    <table id="trades"><thead>
      <tr><th>Time (UTC)</th><th>Type</th><th>Price</th><th>Units</th><th>Fee</th><th>PnL</th><th>Cash</th><th>Coin</th></tr>
    </thead><tbody></tbody></table>
  </div>

  <div style="margin:12px 0;"><a href="/api/state">/api/state</a></div>

<script>
const $ = (id)=>document.getElementById(id);
function fmtUsd(x){ if(x==null) return "—"; return "$"+Number(x).toLocaleString(undefined,{maximumFractionDigits:2}); }
function fmtNum(x,n=6){ if(x==null) return "—"; return Number(x).toFixed(n).replace(/\.?0+$/,''); }
function setText(id,t){ const el=$(id); if(el) el.textContent=t; }

async function load(){
  const r = await fetch('/api/state'); const data = await r.json();
  const s = data.state||{}; const t = data.trades||[];
  setText('updated', '• Updated: '+(s.updated_at||'—'));
  setText('symbol', s.symbol||'—');
  setText('position', (s.position||'—') + (s.entry_price ? ` @ ${fmtNum(s.entry_price,2)}` : ''));
  setText('last_price', fmtNum(s.last_price,2));
  setText('start_cash', fmtUsd(s.start_cash_usd));
  setText('start_coin', fmtNum(s.start_coin_units,6));
  setText('cash', fmtUsd(s.cash_usd));
  setText('coin', fmtNum(s.coin_units,6));
  setText('equity', fmtUsd(s.equity_usd));
  const pnlEl = $('pnl');
  pnlEl.textContent = fmtUsd(s.pnl_usd);
  pnlEl.className = 'value ' + ((s.pnl_usd||0)>=0 ? 'pnl-pos':'pnl-neg');
  setText('fees', fmtUsd(s.fees_paid_usd));
  setText('signal', s.last_signal||'—');

  // trades
  $('tradeCount').textContent = `${t.length} total`;
  const body = document.querySelector('#trades tbody');
  body.innerHTML = t.slice(-10).reverse().map(x=>`
    <tr>
      <td>${x.t||''}</td>
      <td>${x.type||''}</td>
      <td>${fmtNum(x.price,2)}</td>
      <td>${fmtNum(x.units,6)}</td>
      <td>${fmtUsd(x.fee_usd)}</td>
      <td>${x.type==='sell'?fmtUsd(x.pnl):''}</td>
      <td>${fmtUsd(x.cash_usd)}</td>
      <td>${fmtNum(x.coin_units,6)}</td>
    </tr>
  `).join('');
}
load(); setInterval(load, 2000);
</script>
</body></html>
    """
    return HTMLResponse(html)

@app.get("/api/state", response_class=JSONResponse)
def api_state():
    s = load(STATE_PATH, {})
    t = load(TRADES_PATH, [])
    return JSONResponse({"state": s, "trades": t[-200:]})
