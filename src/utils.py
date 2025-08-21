from __future__ import annotations
import json, os, time, random
from typing import Dict, Any
import numpy as np

def make_rng(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)

def write_manifest(run_dir: str, manifest: Dict[str, Any]) -> None:
    os.makedirs(run_dir, exist_ok=True)
    manifest["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    manifest["git_commit"] = os.popen("git rev-parse --short HEAD").read().strip() or ""
    with open(os.path.join(run_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
