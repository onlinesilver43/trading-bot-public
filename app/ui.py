import os, json, io, zipfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

DATA_DIR  = os.getenv("DATA_DIR", "/data")
STATE_PATH  = os.getenv("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH = os.getenv("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))

FILES = [
    "paper_state.json",
    "paper_trades.json",
    "trades_detailed.json",
    "candles_with_signals.json",
    "state_snapshots.json",
    "bot_config.json",
]

app = FastAPI()

def load(path, default):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception: return default

@app.get("/", response_class=HTMLResponse)
def home():
    html = """
<!doctype html><html><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Trading Bots – Status</title>
<style>
:root{--bg:#0b1020;--card:#141a2d;--text:#e8ecff;--muted:#9aa4c7;--accent:#6ea8fe;--green:#41d1a7;--red:#ff6b6b}
*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial}
h1{margin:0 0 16px;font-size:28px}.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.value{font-weight:700;font-size:20px}
.row{display:flex;justify-content:space-between;gap:12px;margin:8px 0}.btn{display:inline-block;padding:10px 14px;border-radius:10px;background:var(--accent);color:#081227;text-decoration:none;font-weight:700}
table{width:100%;border-collapse:collapse}th,td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.06);text-align:left}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.pnl-pos{color:var(--green)}.pnl-neg{color:var(--red)}a{color:var(--accent)}.muted{color:var(--muted)}.pill{display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(255,255,255,.08);font-size:12px}
</style>
</head><body>
<h1>Trading Bots – Status <span class="muted" id="updated"></span></h1>
<div style="margin:0 0 16px;">
  <a class="btn" href="/api/export.zip">Export Diagnostics (ZIP)</a>
  &nbsp; <a href="/exports">Exports</a>
</div>

<div id="cards"></div>

<div class="card" style="margin-top:16px;">
  <div class="row"><div class="label">Recent Trades</div><div class="muted" id="tradeCount"></div></div>
  <table id="trades"><thead>
    <tr><th>Time (UTC)</th><th>Type</th><th>Price</th><th>Units</th><th>Fee</th><th>PnL</th><th>Cash</th><th>Coin</th></tr>
  </thead><tbody></tbody></table>
</div>

<div style="margin:12px 0;"><a href="/api/state">/api/state</a></div>

<script>
const $=(id)=>document.getElementById(id);
function usd(x){return x==null?"—":"$"+Number(x).toLocaleString(undefined,{maximumFractionDigits:2})}
function num(x,n=6){return x==null?"—":Number(x).toFixed(n).replace(/\.?0+$/,'')}
function set(id,t){const e=$(id); if(e) e.textContent=t;}

function render(state){
  const s=state.state||{}; const t=state.trades||[];
  $('updated').textContent='• '+(s.updated_at||'—');
  const pnlClass=(v)=>((v||0)>=0?'pnl-pos':'pnl-neg');
  const html = `
  <div class="grid">
    <div class="card">
      <div class="row"><div class="label">Symbol</div><div class="value">${s.symbol||'—'}</div></div>
      <div class="row"><div class="label">Position</div><div class="value">${(s.position||'—') + (s.entry_price?` @ ${num(s.entry_price,2)}`:'')}</div></div>
      <div class="row"><div class="label">Last price</div><div class="value">${num(s.last_price,2)}</div></div>
      <div class="row"><div class="label">Action/Skip</div><div class="value">${(s.last_action||'—') + (s.skip_reason?` / ${s.skip_reason}`:'')}</div></div>
    </div>

    <div class="card">
      <div class="label">Starting</div>
      <div class="row"><div>Cash (USD)</div><div class="value">${usd(s.start_cash_usd)}</div></div>
      <div class="row"><div>Coin (units)</div><div class="value">${num(s.start_coin_units,6)}</div></div>
    </div>

    <div class="card">
      <div class="label">Current</div>
      <div class="row"><div>Cash (USD)</div><div class="value">${usd(s.cash_usd)}</div></div>
      <div class="row"><div>Coin (units)</div><div class="value">${num(s.coin_units,6)}</div></div>
      <div class="row"><div>Equity (USD)</div><div class="value">${usd(s.equity_usd)}</div></div>
    </div>

    <div class="card">
      <div class="label">PnL</div>
      <div class="row"><div>Realized PnL</div><div class="value ${pnlClass(s.pnl_usd)}">${usd(s.pnl_usd)}</div></div>
      <div class="row"><div>Unrealized PnL</div><div class="value ${pnlClass(s.unrealized_pnl_usd)}">${usd(s.unrealized_pnl_usd)}</div></div>
      <div class="row"><div>Fees paid</div><div class="value">${usd(s.fees_paid_usd)}</div></div>
    </div>
  </div>`;
  document.getElementById('cards').innerHTML = html;

  $('tradeCount').textContent=`${t.length} total`;
  const body=document.querySelector('#trades tbody');
  body.innerHTML=t.slice(-10).reverse().map(x=>`
    <tr>
      <td>${x.t||''}</td>
      <td>${x.type||''}</td>
      <td>${num(x.price,2)}</td>
      <td>${num(x.units,6)}</td>
      <td>${usd(x.fee_usd)}</td>
      <td>${x.type==='sell'?usd(x.pnl):''}</td>
      <td>${usd(x.cash_usd)}</td>
      <td>${num(x.coin_units,6)}</td>
    </tr>`).join('');
}

async function load(){ const r=await fetch('/api/state'); render(await r.json()); }
load(); setInterval(load, 2000);
</script></body></html>
    """
    return HTMLResponse(html)

@app.get("/exports", response_class=HTMLResponse)
def exports_page():
    rows=[]
    for fn in FILES:
        p=os.path.join(DATA_DIR, fn)
        exists=os.path.isfile(p)
        size=os.path.getsize(p) if exists else 0
        rows.append((fn, exists, size))
    rows_html="".join([f"<tr><td><a href=\"/exports/view/{fn}\">{fn}</a></td><td>{'yes' if e else 'no'}</td><td>{s}</td></tr>" for fn,e,s in rows])
    html=f"""<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Exports</title>
    <style>body{{font:14px system-ui;margin:20px}} table{{border-collapse:collapse}} td,th{{padding:8px 12px;border:1px solid #ccc}}</style>
    <h2>Exports</h2>
    <p><a href="/api/export.zip">Export Diagnostics (ZIP)</a></p>
    <table><tr><th>File</th><th>Exists</th><th>Size (bytes)</th></tr>{rows_html}</table>
    </html>"""
    return HTMLResponse(html)

@app.get("/exports/view/{name}", response_class=HTMLResponse)
def view_json(name: str):
    if name not in FILES: raise HTTPException(404, "Unknown file")
    p=os.path.join(DATA_DIR, name)
    if not os.path.isfile(p): raise HTTPException(404, f"{name} not found")
    try:
        with open(p,"r",encoding="utf-8") as f: data=json.load(f)
        body=json.dumps(data, indent=2)
    except Exception:
        with open(p,"r",encoding="utf-8") as f: body=f.read()
    return HTMLResponse(f"<pre style='white-space:pre-wrap'>{body}</pre>")

@app.get("/api/state", response_class=JSONResponse)
def api_state():
    s = load(STATE_PATH, {})
    t = load(TRADES_PATH, [])
    return JSONResponse({"state": s, "trades": t[-200:]})

@app.get("/api/export.zip")
def api_export_zip():
    present=[]
    for fn in FILES:
        p=os.path.join(DATA_DIR, fn)
        if os.path.isfile(p): present.append((fn,p))
    if not present:
        raise HTTPException(status_code=404, detail="No diagnostics files exist yet.")
    buf=io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        for fn,p in present:
            z.write(p, arcname=fn)
    buf.seek(0)
    headers={"Content-Disposition": 'attachment; filename="trading-bot-export.zip"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
