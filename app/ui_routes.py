import os, json, time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from app.ui_helpers import load_json, zip_dirs

# --- Paths (containers get these via compose env) ---
DATA_DIR      = os.getenv("DATA_DIR", "/data")
STATE_PATH    = os.getenv("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH   = os.getenv("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))
CONFIG_PATH   = os.path.join(DATA_DIR, "bot_config.json")
HOST_APP      = os.getenv("HOST_APP", "/host_app")            # /srv/trading-bots/app (ro)
HOST_COMPOSE  = os.getenv("HOST_COMPOSE", "/host_compose")    # /srv/trading-bots/compose (ro)
HOST_GITHUB   = os.getenv("HOST_GITHUB", "/host_github")      # /srv/trading-bots/.github (ro)

DIAG_FILES = [
    "paper_state.json", "paper_trades.json",
    "trades_detailed.json", "candles_with_signals.json",
    "state_snapshots.json", "bot_config.json",
]

TEMPLATE_INDEX = os.path.join(os.path.dirname(__file__), "ui_templates", "index.html")

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    try:
        with open(TEMPLATE_INDEX, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        raise HTTPException(500, f"Template not found: {e}")
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
    if name not in DIAG_FILES:
        raise HTTPException(404, "Unknown file")
    p=os.path.join(DATA_DIR, name)
    if not os.path.isfile(p):
        raise HTTPException(404, f"{name} not found")
    try:
        with open(p,"r",encoding="utf-8") as f:
            data=json.load(f); body=json.dumps(data, indent=2)
    except Exception:
        with open(p,"r",encoding="utf-8") as f:
            body=f.read()
    return HTMLResponse(f"<pre style='white-space:pre-wrap'>{body}</pre>")

@app.get("/api/state", response_class=JSONResponse)
def api_state():
    s = load_json(STATE_PATH, {})
    t = load_json(TRADES_PATH, [])
    return JSONResponse({"state": s, "trades": t[-200:]})

@app.get("/api/export.zip")
def api_export_zip():
    present=[]
    for fn in DIAG_FILES:
        p=os.path.join(DATA_DIR, fn)
        if os.path.isfile(p):
            present.append((fn,p))
    if not present:
        raise HTTPException(status_code=404, detail="No diagnostics files exist yet.")
    buf = zip_dirs(present, zip_root="")
    return StreamingResponse(buf, media_type="application/zip",
    headers={'Content-Disposition': 'attachment; filename="trading-bot-source.zip"'}
    )

@app.get("/api/source.zip")
def api_source_zip():
    pairs = [
        ("app",      HOST_APP if os.path.isdir(HOST_APP) else None),
        ("compose",  HOST_COMPOSE if os.path.isdir(HOST_COMPOSE) else None),
        (".github",  os.path.join(HOST_GITHUB, "workflows") if os.path.isdir(os.path.join(HOST_GITHUB,"workflows")) else None),
    ]
    buf = zip_dirs(pairs, "trading-bot-source")
    if buf is None:
        raise HTTPException(404, "No source directories are mounted in UI container.")
    return StreamingResponse(buf, media_type="application/zip",
    headers={'Content-Disposition': 'attachment; filename="trading-bot-source.zip"'}
    )

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

# --- build meta router (created) ---
from fastapi import APIRouter
router = APIRouter()

try:
    from build_meta import get_build_meta
except Exception:
    def get_build_meta():
        return {"branch":"unknown","deploy_tag":"unknown","commit":"unknown","image":"","updated_at":""}

@router.get("/api/meta")
def api_meta():
    return get_build_meta()
