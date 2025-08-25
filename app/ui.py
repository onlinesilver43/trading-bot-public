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
    # Serve template; fall back to previous inline HTML if the file is missing
    try:
        tpl = os.path.join(os.path.dirname(__file__), "ui_templates", "index.html")
        with open(tpl, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception:
        # fallback: keep your previous inline UI (unchanged)
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
.row{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.btn{display:inline-block;padding:8px 10px;border-radius:10px;background:#1c2440;color:#fff;text-decoration:none;border:1px solid #2b375f}
.badge{display:inline-block;padding:2px 6px;border-radius:6px;background:#1c2440;border:1px solid #2b375f;color:#c8d3ff}
table{width:100%;border-collapse:collapse}th,td{padding:6px 8px;border-bottom:1px solid #223}
kbd{background:#10162a;border:1px solid #2b375f;border-bottom-color:#172040;border-radius:6px;padding:1px 6px;color:#cbd5ff}
.small{font-size:12px;color:var(--muted)}
.mono{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace}
.ok{color:var(--green)}.warn{color:var(--warn)}.err{color:var(--red)}
/* scroll */
pre,code{white-space:pre-wrap;word-break:break-word}
</style>
</head><body>
<h1>Trading Bots – Status</h1>
<div class="grid">
  <div class="card">
    <div class="row">
      <div><div class="label">Symbol</div><div class="value mono" id="symbol">-</div></div>
      <div><div class="label">Equity</div><div class="value mono" id="equity">-</div></div>
      <div><div class="label">Cash</div><div class="value mono" id="cash">-</div></div>
      <div><div class="label">Coins</div><div class="value mono" id="coins">-</div></div>
    </div>
    <div class="row" style="margin-top:10px">
      <a class="btn" href="/api/export.zip">Export Diagnostics (ZIP)</a>
      <a class="btn" href="/api/source.zip">Export Source (ZIP)</a>
      <a class="btn" href="/exports">Exports</a>
      <a class="btn" href="/logs">Logs</a>
      <span class="small">UI refreshes every 2s</span>
    </div>
  </div>
  <div class="card"><div class="label">Recent Trades</div><div id="trades" class="small">Loading…</div></div>
  <div class="card"><div class="label">Engine</div><div id="engine" class="small">Loading…</div></div>
</div>
<div class="card" style="margin-top:16px">
  <div class="row">
    <div>
      <div class="label">Actions</div>
      <div class="small">Hard reset deletes <code>paper_state.json</code>, <code>paper_trades.json</code>, <code>trades_detailed.json</code>, <code>state_snapshots.json</code>, <code>candles_with_signals.json</code>, <code>bot_config.json</code>.</div>
    </div>
    <div class="row"><button class="btn" id="hardReset">Hard Reset (paper)</button></div>
  </div>
</div>
<script>
/* existing logic – unchanged */
const $ = sel => document.querySelector(sel);
async function refresh(){
  try{
    const r=await fetch("/api/state");
    if(!r.ok) return;
    const j=await r.json();
    const s=j.state||{};
    $("#symbol").textContent = s.symbol || "-";
    $("#equity").textContent = typeof s.equity_usd==="number"? `$${s.equity_usd.toFixed(2)}` : "-";
    $("#cash").textContent   = typeof s.cash_usd==="number"? `$${s.cash_usd.toFixed(2)}` : "-";
    $("#coins").textContent  = typeof s.coin_units==="number"? s.coin_units.toFixed(8) : "-";
    const engine = document.querySelector("#engine");
    if(engine){
      engine.innerHTML = `
        Timeframe: <span class="mono">${s.timeframe||"-"}</span><br/>
        Profile: <span class="mono">${s.profile||"-"}</span><br/>
        Position: <span class="mono">${s.position||"-"}</span><br/>
        Last: <span class="mono">${s.last_action||"-"}</span> / Signal: <span class="mono">${s.last_signal||"-"}</span><br/>
        Updated: <span class="mono">${s.updated_at||"-"}</span><br/>
        Skip reason: <span class="mono">${s.skip_reason||"-"}</span>`;
    }
    const trades = document.querySelector("#trades");
    if(trades){
      const ts = (j.trades||[]).slice(-12).reverse();
      if(!ts.length){ trades.textContent="No trades yet."; }
      else{
        trades.innerHTML = ts.map(t=>{
          const u = typeof t.units==="number" ? t.units : 0;
          const amt = Math.abs(u).toFixed(8);
          const typ = (t.type||"").toUpperCase();
          const fee = typeof t.fee_usd==="number" ? `, fee $${t.fee_usd.toFixed(2)}` : "";
          return `<div>• ${t.t} — <span class="mono">${typ}</span> @ <span class="mono">${t.price}</span> (${amt}u${fee})</div>`;
        }).join("");
      }
    }
  }catch(e){} finally{ setTimeout(refresh, 2000); }
}
refresh();
document.getElementById("hardReset")?.addEventListener("click", async ()=>{
  if(!confirm("Hard reset paper state and diagnostics?")) return;
  const r = await fetch("/api/reset", {method:"POST"}); let j={}; try{ j=await r.json(); }catch(_){}
  alert(r.ok ? ('Reset done: '+((j.removed||[]).join(', ')||'nothing to delete')) : ('Reset failed: '+(j.detail||r.status)));
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

# --- Build meta UI additions ---
try:
    from build_meta import get_build_meta
except Exception:
    def get_build_meta():
        return {"branch":"unknown","deploy_tag":"unknown","commit":"unknown","image":"","updated_at":""}

from fastapi import APIRouter
try:
    app
except NameError:
    from fastapi import FastAPI
    app = FastAPI()
router_meta = APIRouter()
@router_meta.get("/api/meta")
def api_meta():
    return get_build_meta()
app.include_router(router_meta)
