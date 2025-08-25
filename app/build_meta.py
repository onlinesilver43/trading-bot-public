import os, datetime as dt

def get_build_meta():
    # Read from env, fall back to 'unknown'
    branch = os.environ.get("GIT_BRANCH", "unknown")
    tag    = os.environ.get("DEPLOY_TAG", "unknown")
    sha    = os.environ.get("GIT_SHA", "unknown")
    image  = os.environ.get("HOSTNAME", "")
    return {
        "branch": branch,
        "deploy_tag": tag,
        "commit": sha,
        "image": image,
        "updated_at": dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()
    }
