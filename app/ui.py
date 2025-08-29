import os
import json
import io
import zipfile
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

# --- Paths (containers get these via compose env) ---
DATA_DIR = os.getenv("DATA_DIR", "/data")
STATE_PATH = os.getenv("STATE_PATH", os.path.join(DATA_DIR, "paper_state.json"))
TRADES_PATH = os.getenv("TRADES_PATH", os.path.join(DATA_DIR, "paper_trades.json"))
HOST_APP = os.getenv("HOST_APP", "/host_app")  # /srv/trading-bots/app (ro)
HOST_COMPOSE = os.getenv("HOST_COMPOSE", "/host_compose")  # /srv/trading-bots/compose (ro)
HOST_GITHUB = os.getenv("HOST_GITHUB", "/host_github")  # /srv/trading-bots/.github (ro)

DIAG_FILES = [
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
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def zip_dirs(pairs, zip_root: str):
    has_any = False
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for label, root in pairs:
            if not root or not os.path.isdir(root):
                continue
            has_any = True
            for dp, dn, fnames in os.walk(root):
                dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
                for fn in fnames:
                    if fn.endswith((".pyc", ".pyo", ".DS_Store")):
                        continue
                    full = os.path.join(dp, fn)
                    rel = os.path.relpath(full, root)
                    z.write(full, arcname=os.path.join(zip_root, label, rel))
    if not has_any:
        return None
    buf.seek(0)
    return buf


@app.get("/", response_class=HTMLResponse)
def home():
    path = os.path.join(os.path.dirname(__file__), "ui_templates", "index.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(
            f"<h1>UI Error</h1><p>Could not load index.html: {e}</p>", status_code=500
        )


@app.get("/exports", response_class=HTMLResponse)
def exports_page():
    rows = []
    for fn in DIAG_FILES:
        p = os.path.join(DATA_DIR, fn)
        exists = os.path.isfile(p)
        size = os.path.getsize(p) if exists else 0
        rows.append((fn, exists, size))
    rows_html = "".join(
        [
            f"<tr><td><a href=\"/exports/view/{fn}\">{fn}</a></td><td>{'yes' if e else 'no'}</td><td>{s}</td></tr>"
            for fn, e, s in rows
        ]
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
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
    p = os.path.join(DATA_DIR, name)
    if not os.path.isfile(p):
        raise HTTPException(404, f"{name} not found")
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            body = json.dumps(data, indent=2)
    except Exception:
        with open(p, "r", encoding="utf-8") as f:
            body = f.read()
    return HTMLResponse(f"<pre style='white-space:pre-wrap'>{body}</pre>")


@app.get("/api/state", response_class=JSONResponse)
def api_state():
    s = load(STATE_PATH, {})
    t = load(TRADES_PATH, [])
    return JSONResponse({"state": s, "trades": t[-200:]})


@app.get("/api/export.zip")
def api_export_zip():
    present = []
    for fn in DIAG_FILES:
        p = os.path.join(DATA_DIR, fn)
        if os.path.isfile(p):
            present.append((fn, p))
    if not present:
        raise HTTPException(status_code=404, detail="No diagnostics files exist yet.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fn, p in present:
            z.write(p, arcname=fn)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="trading-bot-export.zip"'
        },
    )


@app.get("/api/source.zip")
def api_source_zip():
    pairs = [
        ("app", HOST_APP if os.path.isdir(HOST_APP) else None),
        ("compose", HOST_COMPOSE if os.path.isdir(HOST_COMPOSE) else None),
        (
            ".github",
            (
                os.path.join(HOST_GITHUB, "workflows")
                if os.path.isdir(os.path.join(HOST_GITHUB, "workflows"))
                else None
            ),
        ),
    ]
    buf = zip_dirs(pairs, "trading-bot-source")
    if buf is None:
        raise HTTPException(404, "No source directories are mounted in UI container.")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="trading-bot-source.zip"'
        },
    )


@app.post("/api/reset")
def api_reset():
    removed = []
    for fn in DIAG_FILES:
        p = os.path.join(DATA_DIR, fn)
        if os.path.isfile(p):
            try:
                os.remove(p)
                removed.append(fn)
            except Exception as e:
                raise HTTPException(500, f"Failed to remove {fn}: {e}")
    return JSONResponse({"status": "ok", "removed": removed})


# --- Build meta UI additions ---
try:
    from build_meta import get_build_meta
except Exception:

    def get_build_meta():
        return {
            "branch": "unknown",
            "deploy_tag": "unknown",
            "commit": "unknown",
            "image": "",
            "updated_at": "",
        }


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


@app.get("/api/retains_total")
def api_retains_total():
    path = os.getenv("TRADES_PATH", "/data/paper_trades.json")
    total = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            arr = json.load(f)
        for t in arr or []:
            t = t or {}
            ty = str(t.get("type", "")).lower()
            r_flag = bool(t.get("retain_to_stash") or t.get("retain"))
            r_pct = float(t.get("retain_pct", 0) or 0)
            r_usd = float(t.get("retain_usd", 0) or 0)
            r_coin = float(t.get("retain_coin_units", 0) or 0)
            r_stash = float(t.get("stash_delta", 0) or 0)
            if ty in ("retain", "retain_to_stash"):
                total += 1
            elif ty == "sell" and (
                r_flag or r_pct > 0 or r_usd > 0 or r_coin > 0 or r_stash > 0
            ):
                total += 1
    except Exception:
        total = 0
    return {"retains_total": int(total)}


# --- NEW: Enhanced Infrastructure & Deployment Management ---

@app.get("/api/system/health")
def api_system_health():
    """Get basic system health status (enhanced features disabled)"""
    return JSONResponse({
        "status": "basic",
        "message": "Enhanced system monitoring temporarily disabled",
        "timestamp": "unknown",
        "system": {"message": "Basic mode"},
        "containers": {"message": "Basic mode"},
        "api_health": {"message": "Basic mode"}
    })


@app.get("/api/system/deployments")
def api_deployments():
    """Get deployment history and available rollbacks"""
    try:
        backup_dir = "/srv/trading-bots-backups"
        deployments = []
        
        if os.path.exists(backup_dir):
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path):
                    stat = os.stat(item_path)
                    deployments.append({
                        "name": item,
                        "created": stat.st_mtime,
                        "size": sum(os.path.getsize(os.path.join(dirpath, filename))
                                  for dirpath, dirnames, filenames in os.walk(item_path)
                                  for filename in filenames)
                    })
        
        # Sort by creation time (newest first)
        deployments.sort(key=lambda x: x["created"], reverse=True)
        
        return JSONResponse({
            "deployments": deployments,
            "current": {
                "branch": os.getenv("GIT_BRANCH", "unknown"),
                "commit": os.getenv("GIT_SHA", "unknown"),
                "deploy_tag": os.getenv("DEPLOY_TAG", "unknown")
            }
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/system/rollback/{backup_name}")
def api_rollback(backup_name: str):
    """Initiate rollback to specific backup (read-only endpoint)"""
    try:
        backup_dir = "/srv/trading-bots-backups"
        backup_path = os.path.join(backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            raise HTTPException(404, f"Backup {backup_name} not found")
        
        # Return backup info (actual rollback done via GitHub Actions)
        stat = os.stat(backup_path)
        return JSONResponse({
            "backup_name": backup_name,
            "exists": True,
            "created": stat.st_mtime,
            "size": sum(os.path.getsize(os.path.join(dirpath, filename))
                      for dirpath, dirnames, filenames in os.walk(backup_path)
                      for filename in filenames),
            "rollback_instructions": "Use GitHub Actions 'Rollback Deployment' workflow with this backup name"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/system/resources")
def api_resources():
    """Get basic system resource usage (enhanced features disabled)"""
    return JSONResponse({
        "status": "basic",
        "message": "Enhanced system monitoring temporarily disabled",
        "memory": {"message": "Basic mode"},
        "disk": {"message": "Basic mode"},
        "network": {"message": "Basic mode"},
        "top_processes": []
    })


@app.get("/deployment", response_class=HTMLResponse)
def deployment_page():
    """Enhanced deployment management dashboard"""
    html = """<!doctype html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>Deployment Management</title>
        <style>
            body { font: 14px system-ui; margin: 20px; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }
            .status-healthy { color: green; }
            .status-degraded { color: orange; }
            .status-error { color: red; }
            table { border-collapse: collapse; width: 100%; }
            td, th { padding: 8px 12px; border: 1px solid #ccc; text-align: left; }
            .button { background: #007cba; color: white; padding: 8px 16px; border: none; border-radius: 3px; cursor: pointer; }
            .button:hover { background: #005a87; }
            .refresh { float: right; }
        </style>
        <script>
            function refreshData() {
                location.reload();
            }
            
            function checkHealth() {
                fetch('/api/system/health')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('health-status').textContent = data.status;
                        document.getElementById('health-status').className = 'status-' + data.status;
                    });
            }
        </script>
    </head>
    <body>
        <h1>Deployment Management Dashboard</h1>
        <button class="button refresh" onclick="refreshData()">Refresh</button>
        
        <div class="section">
            <h2>System Health</h2>
            <p>Status: <span id="health-status" class="status-healthy">Loading...</span></p>
            <button class="button" onclick="checkHealth()">Check Health</button>
            <p><a href="/api/system/health">View Full Health Data</a></p>
        </div>
        
        <div class="section">
            <h2>Deployment Status</h2>
            <p><a href="/api/system/deployments">View Deployment History</a></p>
            <p><a href="/api/system/resources">View System Resources</a></p>
        </div>
        
        <div class="section">
            <h2>Quick Actions</h2>
            <p><a href="/">← Back to Main Dashboard</a></p>
            <p><a href="/exports">View Exports</a></p>
        </div>
        
        <script>
            // Auto-check health on page load
            checkHealth();
        </script>
    </body>
    </html>"""
    return HTMLResponse(html)


# --- NEW: History Fetcher UI Integration ---

@app.get("/api/history/manifest")
def api_history_manifest():
    """Get history data manifest and inventory"""
    try:
        history_dir = "/srv/trading-bots/history"
        manifest_path = os.path.join(history_dir, "manifest.json")
        
        if not os.path.exists(manifest_path):
            return JSONResponse({
                "status": "no_data",
                "message": "No history data has been fetched yet"
            })
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        return JSONResponse({
            "status": "available",
            "manifest": manifest,
            "summary": {
                "total_files": manifest.get("statistics", {}).get("total_files", 0),
                "total_size_mb": round(manifest.get("statistics", {}).get("total_size_bytes", 0) / (1024 * 1024), 2),
                "symbols": list(manifest.get("data", {}).keys()),
                "intervals": list(manifest.get("statistics", {}).get("intervals", {}).keys()),
                "last_updated": manifest.get("last_updated", "unknown")
            }
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/history/status")
def api_history_status():
    """Get history fetcher status and directory information"""
    try:
        history_dir = "/srv/trading-bots/history"
        
        if not os.path.exists(history_dir):
            return JSONResponse({
                "status": "not_initialized",
                "message": "History directory does not exist"
            })
        
        # Check directory structure
        raw_dir = os.path.join(history_dir, "raw")
        csv_dir = os.path.join(history_dir, "csv")
        parquet_dir = os.path.join(history_dir, "parquet")
        
        status = {
            "base_directory": history_dir,
            "directories": {
                "raw": {
                    "exists": os.path.exists(raw_dir),
                    "file_count": len(os.listdir(raw_dir)) if os.path.exists(raw_dir) else 0,
                    "size_mb": round(sum(os.path.getsize(os.path.join(raw_dir, f)) for f in os.listdir(raw_dir) if os.path.isfile(os.path.join(raw_dir, f))) / (1024 * 1024), 2) if os.path.exists(raw_dir) else 0
                },
                "csv": {
                    "exists": os.path.exists(csv_dir),
                    "file_count": len(os.listdir(csv_dir)) if os.path.exists(csv_dir) else 0,
                    "size_mb": round(sum(os.path.getsize(os.path.join(csv_dir, f)) for f in os.listdir(csv_dir) if os.path.isfile(os.path.join(csv_dir, f))) / (1024 * 1024), 2) if os.path.exists(csv_dir) else 0
                },
                "parquet": {
                    "exists": os.path.exists(parquet_dir),
                    "file_count": len([f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]) if os.path.exists(parquet_dir) else 0,
                    "size_mb": round(sum(os.path.getsize(os.path.join(parquet_dir, f)) for f in os.listdir(parquet_dir) if f.endswith('.parquet')) / (1024 * 1024), 2) if os.path.exists(parquet_dir) else 0
                }
            }
        }
        
        # Check manifest
        manifest_path = os.path.join(history_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                status["manifest"] = {
                    "exists": True,
                    "last_updated": manifest.get("last_updated", "unknown"),
                    "total_files": manifest.get("statistics", {}).get("total_files", 0)
                }
            except Exception as e:
                status["manifest"] = {"exists": True, "error": str(e)}
        else:
            status["manifest"] = {"exists": False}
        
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/history/symbols/{symbol}")
def api_history_symbol(symbol: str):
    """Get detailed information for a specific symbol"""
    try:
        history_dir = "/srv/trading-bots/history"
        manifest_path = os.path.join(history_dir, "manifest.json")
        
        if not os.path.exists(manifest_path):
            raise HTTPException(404, "No history data available")
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        if symbol not in manifest.get("data", {}):
            raise HTTPException(404, f"Symbol {symbol} not found in history data")
        
        symbol_data = manifest["data"][symbol]
        
        # Calculate additional statistics
        total_size = 0
        file_counts = {}
        
        for interval, files in symbol_data.items():
            file_counts[interval] = len(files)
            for file_info in files:
                total_size += file_info.get("size_bytes", 0)
        
        return JSONResponse({
            "symbol": symbol,
            "intervals": list(symbol_data.keys()),
            "file_counts": file_counts,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": symbol_data
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/history", response_class=HTMLResponse)
def history_page():
    """Enhanced history fetcher dashboard"""
    html = """<!doctype html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>History Fetcher Dashboard</title>
        <style>
            body { font: 14px system-ui; margin: 20px; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }
            .status-healthy { color: green; }
            .status-degraded { color: orange; }
            .status-error { color: red; }
            table { border-collapse: collapse; width: 100%; }
            td, th { padding: 8px 12px; border: 1px solid #ccc; text-align: left; }
            .button { background: #007cba; color: white; padding: 8px 16px; border: none; border-radius: 3px; cursor: pointer; }
            .button:hover { background: #005a87; }
            .refresh { float: right; }
        </style>
        <script>
            function refreshData() {
                location.reload();
            }
            
            function checkStatus() {
                fetch('/api/history/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status-status').textContent = data.status;
                        document.getElementById('status-status').className = 'status-' + data.status;
                        document.getElementById('status-message').textContent = data.message;
                        document.getElementById('status-message').style.display = 'block';
                        
                        // Update directory sizes
                        document.getElementById('raw-size').textContent = data.directories.raw.size_mb + ' MB';
                        document.getElementById('csv-size').textContent = data.directories.csv.size_mb + ' MB';
                        document.getElementById('parquet-size').textContent = data.directories.parquet.size_mb + ' MB';
                        
                        // Update manifest info
                        document.getElementById('manifest-exists').textContent = data.manifest.exists ? 'Yes' : 'No';
                        document.getElementById('manifest-last-updated').textContent = data.manifest.last_updated;
                        document.getElementById('manifest-total-files').textContent = data.manifest.total_files;
                    });
            }

            function fetchManifest() {
                fetch('/api/history/manifest')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'available') {
                            document.getElementById('manifest-data').textContent = JSON.stringify(data.manifest, null, 2);
                            document.getElementById('manifest-summary').textContent = JSON.stringify(data.summary, null, 2);
                        } else {
                            document.getElementById('manifest-data').textContent = 'No manifest data available.';
                            document.getElementById('manifest-summary').textContent = 'No manifest data available.';
                        }
                    });
            }

            function fetchSymbolDetails(symbol) {
                fetch(`/api/history/symbols/${symbol}`)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('symbol-details').textContent = JSON.stringify(data, null, 2);
                    });
            }
        </script>
    </head>
    <body>
        <h1>History Fetcher Dashboard</h1>
        <button class="button refresh" onclick="refreshData()">Refresh</button>
        
        <div class="section">
            <h2>History Fetcher Status</h2>
            <p>Status: <span id="status-status" class="status-healthy">Loading...</span></p>
            <p id="status-message" style="display: none;"></p>
            <button class="button" onclick="checkStatus()">Check Status</button>
            <p><a href="/api/history/status">View Full Status Data</a></p>
        </div>
        
        <div class="section">
            <h2>History Data Manifest</h2>
            <button class="button" onclick="fetchManifest()">Fetch Manifest</button>
            <pre id="manifest-data"></pre>
            <h3>Summary</h3>
            <pre id="manifest-summary"></pre>
        </div>

        <div class="section">
            <h2>Symbol Details</h2>
            <input type="text" id="symbol-input" placeholder="Enter symbol (e.g., BTCUSDT)">
            <button class="button" onclick="fetchSymbolDetails(document.getElementById('symbol-input').value)">Fetch Symbol Details</button>
            <pre id="symbol-details"></pre>
        </div>
        
        <div class="section">
            <h2>Quick Actions</h2>
            <p><a href="/">← Back to Main Dashboard</a></p>
            <p><a href="/api/history/manifest">View Manifest</a></p>
            <p><a href="/api/history/status">View Status</a></p>
        </div>
        
        <script>
            // Auto-check status on page load
            checkStatus();
        </script>
    </body>
    </html>"""
    return HTMLResponse(html)
