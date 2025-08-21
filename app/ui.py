# app/ui.py
# FastAPI UI with invariant endpoints and small quality-of-life additions.
import os, io, json, zipfile, shutil, glob
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse

DATA_DIR = os.environ.get("DATA_DIR", "/srv/trading-bots/data")
APP_DIR = os.environ.get("APP_DIR", "/srv/trading-bots/app")

app = FastAPI(title="tb-ui")

def jload(p, d): 
    try:
        with open(p, "r", encoding="utf-8") as f: 
            return json.load(f)
    except: 
        return d

@app.get("/api/state")
def api_state():
    state = jload(f"{DATA_DIR}/paper_state.json", {})
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
        readme = (
            "# Trading Bot Export\n"
            f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
            "Contains: state, trades, detailed, candles_with_signals, snapshots, bot_config\n"
        )
        z.writestr("README.txt", readme)
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip", headers={"Content-Disposition":"attachment; filename=export.zip"})

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
    return StreamingResponse(mem, media_type="application/zip", headers={"Content-Disposition":"attachment; filename=source.zip"})

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
# --- Runner to keep container alive ---
if __name__ == "__main__":
    # Start FastAPI app with Uvicorn inside the container
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
