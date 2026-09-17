"""Serverless entry point.

Two jobs:

1. RunPod's GitHub build refuses to deploy unless it finds
   `runpod.serverless.start()` in the repository itself. It cannot see the
   handler inherited from the runpod/worker-comfyui base image, so this file
   finds that handler and starts it.

2. The base handler only returns `images` from a workflow's outputs. This one
   renders video, so anything the base handler misses is picked up here: the
   output directory is checked for video files written while the job ran, and
   each is returned base64-encoded alongside the images.
"""

import base64
import importlib.util
import os
import sys
import time

import runpod

BASE_HANDLER = os.environ.get("COMFY_HANDLER_PATH", "/handler.py")
OUTPUT_DIR = os.environ.get("COMFY_OUTPUT_DIR", "/comfyui/output")
VIDEO_SUFFIXES = (".mp4", ".webm", ".mkv", ".gif", ".webp", ".mov")
# A base64 payload has to come back inside the job response, and RunPod caps
# that. Anything larger is reported by name rather than silently dropped.
MAX_RETURN_BYTES = int(os.environ.get("MAX_VIDEO_RETURN_BYTES", 8 * 1024 * 1024))


def _load_base_handler():
    if not os.path.isfile(BASE_HANDLER):
        return None
    spec = importlib.util.spec_from_file_location("comfyui_worker_handler", BASE_HANDLER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["comfyui_worker_handler"] = module
    spec.loader.exec_module(module)
    return getattr(module, "handler", None)


def _videos_written_since(since):
    found = []
    for root, _dirs, files in os.walk(OUTPUT_DIR):
        for name in files:
            if not name.lower().endswith(VIDEO_SUFFIXES):
                continue
            path = os.path.join(root, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_mtime < since:
                continue
            found.append((path, st.st_size))
    found.sort(key=lambda p: os.path.getmtime(p[0]))
    return found


def _encode(path, size):
    if size > MAX_RETURN_BYTES:
        return {
            "filename": os.path.basename(path),
            "type": "too_large",
            "bytes": size,
            "data": None,
            "note": "larger than MAX_VIDEO_RETURN_BYTES; set BUCKET_ENDPOINT_URL "
                    "to have outputs uploaded instead",
        }
    with open(path, "rb") as fh:
        return {
            "filename": os.path.basename(path),
            "type": "base64",
            "bytes": size,
            "data": base64.b64encode(fh.read()).decode("utf-8"),
        }


def make_handler(base):
    def wrapped(job):
        started = time.time() - 1  # a second of slack for clock granularity
        result = base(job)
        if not isinstance(result, dict):
            return result
        videos = [_encode(p, s) for p, s in _videos_written_since(started)]
        if videos:
            result["videos"] = videos
        elif not result.get("images"):
            # Neither kind of output: say so rather than returning an empty success.
            result.setdefault("errors", []).append(
                f"no images and no video files found in {OUTPUT_DIR} after the run"
            )
        return result

    return wrapped


def _missing(job):
    return {
        "error": f"the ComfyUI handler was not found at {BASE_HANDLER}; "
                 "set COMFY_HANDLER_PATH to its location"
    }


if __name__ == "__main__":
    base = _load_base_handler()
    runpod.serverless.start({"handler": make_handler(base) if base else _missing})
