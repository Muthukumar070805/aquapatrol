#!/usr/bin/env bash
# Optionally fetch the YOLO checkpoint from the Hugging Face Hub before
# starting the server. Set OILSPILL_YOLO_HF_REPO (e.g. "user/oil-spill-yolo")
# and optionally OILSPILL_YOLO_HF_FILE (default best.pt). The file is placed at
# OILSPILL_API_YOLO_WEIGHTS (default /app/artifacts/yolo/best.pt). Without
# weights the API still starts and serves; YOLO endpoints return 503 until
# weights are present (e.g. mounted into the container).
set -euo pipefail

WEIGHTS_PATH="${OILSPILL_API_YOLO_WEIGHTS:-/app/artifacts/yolo/best.pt}"
MODEL_FILE="${OILSPILL_YOLO_HF_FILE:-best.pt}"
mkdir -p "$(dirname "$WEIGHTS_PATH")"

if [ -n "${OILSPILL_YOLO_HF_REPO:-}" ] && [ ! -f "$WEIGHTS_PATH" ]; then
  echo "fetching $MODEL_FILE from HF repo $OILSPILL_YOLO_HF_REPO ..."
  WEIGHTS_PATH="$WEIGHTS_PATH" MODEL_FILE="$MODEL_FILE" python - <<'PY' || echo "weights fetch failed; YOLO endpoints will serve 503"
import os
import shutil
from huggingface_hub import hf_hub_download
repo = os.environ["OILSPILL_YOLO_HF_REPO"]
fname = os.environ.get("MODEL_FILE", "best.pt")
dest = os.environ.get("WEIGHTS_PATH", "/app/artifacts/yolo/best.pt")
path = hf_hub_download(repo_id=repo, filename=fname, local_dir=os.path.dirname(dest))
if os.path.abspath(path) != os.path.abspath(dest):
    shutil.copyfile(path, dest)
print("downloaded", dest)
PY
fi

exec "$@"
