import os, json, io, zipfile

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def zip_dirs(pairs, zip_root: str):
    """pairs = [(label, root_dir_or_None), ...]"""
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
                    if fn.endswith((".pyc",".pyo",".DS_Store")):
                        continue
                    full = os.path.join(dp, fn)
                    rel  = os.path.relpath(full, root)
                    z.write(full, arcname=os.path.join(zip_root, label, rel))
    if not has_any:
        return None
    buf.seek(0)
    return buf
