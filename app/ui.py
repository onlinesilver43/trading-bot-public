import json, os
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
    html = """
<!doctype html>
<html><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Trading Bots – Status</title>
<style>
:root{--bg:#0b1020;--card:#141a2d;--text:#e8ecff;--muted:#9aa4c7;--accent:#6ea8fe;--green:#41d1a7;--red:#ff6b6b}
*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial}
h1{margin:0 0 16px;font-size:28px}.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.value{font-weight:700;font-size:20px}
.row{display:flex;justify-content:space-between;gap:12px;margin:8px 0}
table{width:100%;border-collapse:collapse}th,td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.06);text-align:left}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.pnl-pos{color:var(--green)}.pnl-neg{color:var(--red)}a{color:var(--accent)}.muted{color:var(--muted)}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(255,255,255,.08);font-size:12px}
</style>
</head><body>
<h1>Trading Bots – Status <span class="muted" id="updated"></span></h1>
<div class="grid">
  <div class="card">
    <div class="row"><div class="label">Symbol</div><div class="value" id="symbol">—</div></div>
    <div class="row"><div class="label">Position</div><div class="value" id="position">—</div></div>
    <div class="row"><div class="label">Last price</div><div class="value" id="last_price">—</div></div>
    <div class="row"><div class="label">Action / Skip</div><div class="value" id="action">—</div></div>
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
    <div class="row"><div>Realized PnL</div><div class="value" id="pnl">—</div></div>
    <div class="row"><div>Unrealized PnL</div><div class="value" id="unpnl">—</div></div>
    <div class="row"><div>Fees paid</div><div class="value" id="fees">—</div></div>
  </div>

  <div class="card">
    <div class="label">Rules</div>
    <div class="row"><div>Confirm bars</div><div class="value" id="r_confirm">—</div></div>
    <div class="row"><div>Cooldown (bars)</div><div class="value" id="r_hold">—</div></div>
    <div class="row"><div>MA threshold</div><div class="value" id="r_thr">—</div></div>
    <div class="row"><div>Min trade</div><div class="value" id="r_min">—</div></div>
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
function usd(x){return x==null?"—":"$"+Number(x).toLocaleString(undefined,{maximumFractionDigits:2});}
function num(x,n=6){return x==null?"—":Number(x).toFixed(n).replace(/\.?0+$/,'');}
function set(id,t){const e=$(id); if(e) e.textContent=t;}

async function load(){
  const r = await fetch('/api/state'); const data = await r.json();
  const s = data.state||{}; const t = data.trades||[];
  set('updated','• '+(s.updated_at||'—'));
  set('symbol', s.symbol||'—');
  set('position', (s.position||'—') + (s.entry_price?` @ ${num(s.entry_price,2)}`:''));
  set('last_price', num(s.last_price,2));
  set('start_cash', usd(s.start_cash_usd)); set('start_coin', num(s.start_coin_units,6));
  set('cash', usd(s.cash_usd)); set('coin', num(s.coin_units,6)); set('equity', usd(s.equity_usd));
  const pnlEl=$('pnl'); pnlEl.textContent=usd(s.pnl_usd); pnlEl.className='value '+((s.pnl_usd||0)>=0?'pnl-pos':'pnl-neg');
  const unEl=$('unpnl'); unEl.textContent=usd(s.unrealized_pnl_usd); unEl.className='value '+((s.unrealized_pnl_usd||0)>=0?'pnl-pos':'pnl-neg');
  set('fees', usd(s.fees_paid_usd));
  set('action', (s.last_action||'—') + (s.skip_reason?` / skip: ${s.skip_reason}`:''));
  const rls=s.rules||{}; set('r_confirm', rls.CONFIRM_BARS??'—'); set('r_hold', rls.MIN_HOLD_BARS??'—');
  set('r_thr', (rls.THRESHOLD_PCT!=null? (Number(rls.THRESHOLD_PCT)*100).toFixed(3)+'%':'—'));
  set('r_min', usd(rls.MIN_TRADE_USD));
  $('tradeCount').textContent=`${t.length} total`;
  const body=document.querySelector('#trades tbody');
  body.innerHTML=t.slice(-10).reverse().map(x=>`
    <tr>
      <td>${x.t||''}</td><td>${x.type||''}</td><td>${num(x.price,2)}</td><td>${num(x.units,6)}</td>
      <td>${usd(x.fee_usd)}</td><td>${x.type==='sell'?usd(x.pnl):''}</td>
      <td>${usd(x.cash_usd)}</td><td>${num(x.coin_units,6)}</td>
    </tr>`).join('');
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
