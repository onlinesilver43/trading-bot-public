import os, json, io, zipfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

# --- Paths (containers get these via compose env) ---
DATA_DIR      = os.getenv("DATA_DIR", "/data")
STATE_PATH    = os.getenv("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH   = os.getenv("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))
HOST_APP      = os.getenv("HOST_APP", "/host_app")            # /srv/trading-bots/app (ro)
HOST_COMPOSE  = os.getenv("HOST_COMPOSE", "/host_compose")    # /srv/trading-bots/compose (ro)
HOST_GITHUB   = os.getenv("HOST_GITHUB", "/host_github")      # /srv/trading-bots/.github (ro)

DIAG_FILES = [
    "paper_state.json", "paper_trades.json",
    "trades_detailed.json", "candles_with_signals.json",
    "state_snapshots.json", "bot_config.json",
]

app = FastAPI()

def load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def zip_dirs(pairs, zip_root: str):
    has_any = False
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for label, root in pairs:
            if not root or not os.path.isdir(root): continue
            has_any = True
            for dp, dn, fnames in os.walk(root):
                dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
                for fn in fnames:
                    if fn.endswith((".pyc",".pyo",".DS_Store")): continue
                    full = os.path.join(dp, fn)
                    rel  = os.path.relpath(full, root)
                    z.write(full, arcname=os.path.join(zip_root, label, rel))
    if not has_any: return None
    buf.seek(0); return buf

@app.get("/", response_class=HTMLResponse)
def home():
    html = """
<!doctype html><html><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Trading Bots – Status</title>
<style>
:root{--bg:#0b1020;--card:#141a2d;--text:#e8ecff;--muted:#9aa4c7;--accent:#6ea8fe;--warn:#ffb74d;--green:#41d1a7;--red:#ff6b6b}
*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial}
h1{margin:0 0 16px;font-size:28px}.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.value{font-weight:700;font-size:20px}
.row{display:flex;justify-content:space-between;gap:12px;margin:8px 0}
.btn{display:inline-block;padding:10px 14px;border-radius:10px;background:var(--accent);color:#081227;text-decoration:none;font-weight:700}
.btn-warn{background:var(--warn);color:#081227}
table{width:100%;border-collapse:collapse}th,td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.06);text-align:left}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.pnl-pos{color:var(--green)}.pnl-neg{color:var(--red)}a{color:var(--accent)}.muted{color:var(--muted)}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:700}
.badge-ok{background:#153d2a;color:#41d1a7}.badge-warn{background:#3e2f14;color:#ffb74d}.badge-err{background:#3d1a1a;color:#ff6b6b}
.small{font-size:12px}
</style>
</head><body>
<h1>Trading Bots – Status <span class="muted" id="updated"></span></h1>

<div style="margin:0 0 16px; display:flex; gap:10px; flex-wrap:wrap;">
  <a class="btn" href="/api/export.zip">Export Diagnostics (ZIP)</a>
  <a class="btn" href="/api/source.zip">Export Source (ZIP)</a>
  <a class="btn" href="/exports">Exports</a>
  <button id="btnReset" class="btn btn-warn" title="Clears paper JSON files on the server.">Hard Reset (paper)</button>
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
function pct(x,n=2){return x==null?"—":(Number(x)*100).toFixed(n).replace(/\.?0+$/,'')+'%'}

function heartbeat(tsStr){
  if(!tsStr) return ["badge-err","stale"];
  const now = Date.now();
  const last = Date.parse(tsStr);
  if(isNaN(last)) return ["badge-err","invalid time"];
  const diff = (now - last)/1000;
  if(diff <= 15) return ["badge-ok", "live"];
  if(diff <= 90) return ["badge-warn", Math.round(diff)+"s behind"];
  return ["badge-err", Math.round(diff/60)+"m behind"];
}

async function load(){
  const [stateRes, cfgRes] = await Promise.all([
    fetch('/api/state'), fetch('/exports/view/bot_config.json').catch(()=>null)
  ]);
  const data = await stateRes.json();
  const s = data.state||{}, t = data.trades||[];
  let cfg = null;
  if(cfgRes && cfgRes.ok){
    const txt = await cfgRes.text();
    try{ cfg = JSON.parse(txt.replace(/^<pre[^>]*>/,'').replace(/<\/pre>$/,'')); }catch(e){ cfg=null; }
  }

  $('updated').textContent='• '+(s.updated_at||'—');
  $('tradeCount').textContent=`${t.length} total`;

  const [hbClass, hbText] = heartbeat(s.updated_at);

  const symbol = s.symbol || (cfg && cfg.symbol) || '—';
  const timeframe = (cfg && cfg.timeframe) || '—';
  const position = s.position || '—';
  const entry = s.entry_price!=null ? ` @ ${num(s.entry_price,2)}` : '';
  const unreal = s.unrealized_pnl_usd;
  const equity = s.equity_usd;

  const cfgRows = cfg ? `
    <div class="row"><div class="label">Pair / TF</div><div class="value">${cfg.symbol||'—'} / ${cfg.timeframe||'—'}</div></div>
    <div class="row"><div>FAST / SLOW</div><div class="value">${cfg.fast_sma_len} / ${cfg.slow_sma_len}</div></div>
    <div class="row"><div>Confirm bars</div><div class="value">${cfg.confirm_bars}</div></div>
    <div class="row"><div>Min hold bars</div><div class="value">${cfg.min_hold_bars}</div></div>
    <div class="row"><div>Threshold</div><div class="value">${pct(cfg.hysteresis_bp?cfg.hysteresis_bp/10000:cfg.threshold_pct)}</div></div>
    <div class="row"><div>Order sizing</div><div class="value">${cfg.order_pct_equity!=null? (pct(cfg.order_pct_equity)+' of equity'):('$'+(cfg.order_size_usd||'—'))}</div></div>
  ` : `<div class="small muted">No bot_config.json yet.</div>`;

  const cardsHTML = `
  <div class="grid">
    <div class="card">
      <div class="row"><div class="label">Bot Summary</div><div class="badge ${hbClass}">${hbText}</div></div>
      <div class="row"><div>Symbol</div><div class="value">${symbol}</div></div>
      <div class="row"><div>Timeframe</div><div class="value">${timeframe}</div></div>
      <div class="row"><div>Position</div><div class="value">${position}${entry}</div></div>
      <div class="row"><div>Last price</div><div class="value">${num(s.last_price,2)}</div></div>
      <div class="row"><div>Equity (USD)</div><div class="value">${usd(equity)}</div></div>
      <div class="row"><div>Unrealized PnL</div><div class="value ${(unreal||0)>=0?'pnl-pos':'pnl-neg'}">${usd(unreal)}</div></div>
      <div class="row"><div>Action/Skip</div><div class="value small">${(s.last_action||'—') + (s.skip_reason?` / ${s.skip_reason}`:'')}</div></div>
    </div>

    <div class="card">
      <div class="row"><div class="label">Config Snapshot</div><div class="muted small">${cfg && cfg.updated_at ? cfg.updated_at : ''}</div></div>
      ${cfgRows}
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
      <div class="row"><div>Fees paid</div><div class="value">${usd(s.fees_paid_usd)}</div></div>
    </div>
  </div>`;
  document.getElementById('cards').innerHTML = cardsHTML;

  const body=document.querySelector('#trades tbody');
  body.innerHTML=t.slice(-10).reverse().map(x=>`
    <tr>
      <td>${x.t||''}</td><td>${x.type||''}</td><td>${num(x.price,2)}</td><td>${num(x.units,6)}</td>
      <td>${usd(x.fee_usd)}</td><td>${x.type==='sell'?usd(x.pnl):''}</td>
      <td>${usd(x.cash_usd)}</td><td>${num(x.coin_units,6)}</td>
    </tr>`).join('');
}
load(); setInterval(load,2000);

document.getElementById('btnReset').addEventListener('click', async ()=>{
  if(!confirm('Hard reset paper data? This clears all JSON state/trades/exports.')) return;
  const r = await fetch('/api/reset', {method:'POST'});
  const j = await r.json().catch(()=>({}));
  alert(r.ok ? ('Reset done: '+(j.removed||[]).join(', ') || 'nothing to delete') : ('Reset failed: '+(j.detail||r.status)));
  setTimeout(()=>location.reload(), 1000);
});
</script></body></html>
    """
    return HTMLResponse(html)

@app.get("/exports", response_class=HTMLResponse)
def exports_page():
    rows=[]
    for fn in DIAG_FILES:
        p=os.path.join(DATA_DIR, fn)
        exists=os.path.isfile(p); size=os.path.getsize(p) if exists else 0
        rows.append((fn, exists, size))
    rows_html="".join([f"<tr><td><a href=\"/exports/view/{fn}\">{fn}</a></td><td>{'yes' if e else 'no'}</td><td>{s}</td></tr>" for fn,e,s in rows])
    html=f"""<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Exports</title>
    <style>body{{font:14px system-ui;margin:20px}} table{{border-collapse:collapse}} td,th{{padding:8px 12px;border:1px solid #ccc}}</style>
    <h2>Exports</h2>
    <p><a href="/api/export.zip">Export Diagnostics (ZIP)</a> &nbsp; <a href="/api/source.zip">Export Source (ZIP)</a></p>
    <table><tr><th>File</th><th>Exists</th><th>Size (bytes)</th></tr>{rows_html}</table>
    </html>"""
    return HTMLResponse(html)

@app.get("/exports/view/{name}", response_class=HTMLResponse)
def view_json(name: str):
    if name not in DIAG_FILES: raise HTTPException(404, "Unknown file")
    p=os.path.join(DATA_DIR, name)
    if not os.path.isfile(p): raise HTTPException(404, f"{name} not found")
    try:
        with open(p,"r",encoding="utf-8") as f: data=json.load(f); body=json.dumps(data, indent=2)
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
    for fn in DIAG_FILES:
        p=os.path.join(DATA_DIR, fn)
        if os.path.isfile(p): present.append((fn,p))
    if not present: raise HTTPException(status_code=404, detail="No diagnostics files exist yet.")
    buf=io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fn,p in present: z.write(p, arcname=fn)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="trading-bot-export.zip"'})

@app.get("/api/source.zip")
def api_source_zip():
    pairs = [
        ("app",      HOST_APP if os.path.isdir(HOST_APP) else None),
        ("compose",  HOST_COMPOSE if os.path.isdir(HOST_COMPOSE) else None),
        (".github",  os.path.join(HOST_GITHUB, "workflows") if os.path.isdir(os.path.join(HOST_GITHUB,"workflows")) else None),
    ]
    buf = zip_dirs(pairs, "trading-bot-source")
    if buf is None: raise HTTPException(404, "No source directories are mounted in UI container.")
    return StreamingResponse(buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="trading-bot-source.zip"'})

@app.post("/api/reset")
def api_reset():
    removed=[]
    for fn in DIAG_FILES:
        p=os.path.join(DATA_DIR, fn)
        if os.path.isfile(p):
            try:
                os.remove(p); removed.append(fn)
            except Exception as e:
                raise HTTPException(500, f"Failed to remove {fn}: {e}")
    return JSONResponse({"status":"ok","removed":removed})
