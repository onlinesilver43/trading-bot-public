# app/ui.py — FastAPI UI with invariant endpoints + index dashboard (auto-refresh)
import os, io, json, zipfile
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse

DATA_DIR = os.environ.get("DATA_DIR", "/srv/trading-bots/data")
APP_DIR  = os.environ.get("APP_DIR",  "/srv/trading-bots/app")

app = FastAPI(title="tb-ui")

def jload(p, d):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return d

# -------- Invariant APIs --------
@app.get("/api/state")
def api_state():
    state  = jload(f"{DATA_DIR}/paper_state.json", {})
    trades = jload(f"{DATA_DIR}/paper_trades.json", [])
    return JSONResponse({"state": state, "trades": trades})

@app.get("/api/export.zip")
def api_export_zip():
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in [
            "paper_state.json","paper_trades.json","trades_detailed.json",
            "candles_with_signals.json","state_snapshots.json","bot_config.json"
        ]:
            p = f"{DATA_DIR}/{name}"
            if os.path.exists(p):
                z.write(p, arcname=name)
        z.writestr(
            "README.txt",
            "# Trading Bot Export\n"
            f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
            "Contains: state, trades, detailed, candles_with_signals, snapshots, bot_config\n"
        )
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip",
                             headers={"Content-Disposition":"attachment; filename=export.zip"})

@app.get("/api/source.zip")
def api_source_zip():
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(APP_DIR):
            for fn in files:
                p = os.path.join(root, fn)
                arc = os.path.relpath(p, APP_DIR)
                z.write(p, arcname=arc)
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip",
                             headers={"Content-Disposition":"attachment; filename=source.zip"})

@app.post("/api/reset")
def api_reset():
    removed = []
    for name in [
        "paper_state.json","paper_trades.json","trades_detailed.json",
        "candles_with_signals.json","state_snapshots.json","bot_config.json"
    ]:
        p = f"{DATA_DIR}/{name}"
        if os.path.exists(p):
            os.remove(p); removed.append(name)
    seed = {"paper": True, "last_skip_reason": "reset", "heartbeat_iso": datetime.now(timezone.utc).isoformat()}
    with open(f"{DATA_DIR}/paper_state.json", "w", encoding="utf-8") as f:
        json.dump(seed, f)
    return JSONResponse({"ok": True, "removed": removed})

# -------- Convenience page (unchanged path) --------
@app.get("/exports")
def exports_page():
    html = """
    <html><head><meta http-equiv="refresh" content="3" />
    <style>body{font-family:system-ui;margin:24px} a{display:block;margin:8px 0}</style>
    </head><body>
    <h2>Trading Bot Exports</h2>
    <a href="/api/export.zip">Download export.zip</a>
    <a href="/api/source.zip">Download source.zip</a>
    <p>State heartbeat updates every closed bar. Refresh is ~2s.</p>
    </body></html>
    """
    return HTMLResponse(html)

# -------- NEW: Root index dashboard (auto-refresh ~2s) --------
@app.get("/")
def index():
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TB — Status</title>
  <meta http-equiv="refresh" content="2">
  <style>
    body{font-family:system-ui;margin:24px;max-width:900px}
    .row{display:flex;gap:24px;flex-wrap:wrap}
    .card{border:1px solid #ddd;border-radius:12px;padding:16px;flex:1 1 280px}
    .muted{color:#666;font-size:12px}
    code{background:#f6f8fa;padding:2px 4px;border-radius:6px}
    a{color:#0b67ff;text-decoration:none}
  </style>
</head>
<body>
  <h2>Trading Bot — Live Status</h2>
  <div class="row">
    <div class="card">
      <h3>State</h3>
      <div id="state">Loading…</div>
      <div class="muted">Auto-refreshes every ~2s</div>
    </div>
    <div class="card">
      <h3>Quick Links</h3>
      <ul>
        <li><a href="/api/state" target="_blank">/api/state</a></li>
        <li><a href="/exports" target="_blank">/exports</a></li>
        <li><a href="/api/export.zip" target="_blank">export.zip</a></li>
        <li><a href="/api/source.zip" target="_blank">source.zip</a></li>
      </ul>
    </div>
  </div>
  <script>
    fetch('/api/state').then(r => r.json()).then(d => {
      const s = d.state || {};
      const rows = [
        ['last_action', s.last_action],
        ['last_skip_reason', s.last_skip_reason],
        ['last_closed_bar_iso', s.last_closed_bar_iso],
        ['heartbeat_iso', s.heartbeat_iso],
        ['bars_since_trade', s.bars_since_trade],
        ['equity_usd', s.equity_usd],
        ['cash_usd', s.cash_usd],
        ['pos_qty', s.pos_qty],
        ['pos_avg', s.pos_avg],
      ].map(([k,v]) => `<tr><td><code>${k}</code></td><td>${v===undefined?'':v}</td></tr>`).join('');
      document.getElementById('state').innerHTML =
        `<table>${rows}</table>`;
    }).catch(e=>{
      document.getElementById('state').textContent = 'Error loading /api/state';
    });
  </script>
</body>
</html>
"""
    return HTMLResponse(html)

# -------- Runner (keeps container alive) --------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
