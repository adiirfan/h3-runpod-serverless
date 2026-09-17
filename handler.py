"""Serverless entry point.

The real work is done by the handler inside the base image
(runpod/worker-comfyui), which already speaks the ComfyUI job format: it takes
`input.workflow` plus optional `input.images` and returns the outputs. This
file exists because RunPod's GitHub build looks for `runpod.serverless.start()`
in the repository itself and will not deploy without it — it cannot see a
handler that is inherited from the base image.

So: find that handler, and start it. If the base module starts the worker on
import (some versions do), this never gets past the import and that is fine.
"""

import importlib.util
import os
import sys

import runpod

# Where the base image keeps its handler. Overridable in case the path moves.
BASE_HANDLER = os.environ.get("COMFY_HANDLER_PATH", "/handler.py")


def _load_base_handler():
    if not os.path.isfile(BASE_HANDLER):
        return None
    spec = importlib.util.spec_from_file_location("comfyui_worker_handler", BASE_HANDLER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["comfyui_worker_handler"] = module
    spec.loader.exec_module(module)
    return getattr(module, "handler", None)


def _missing(job):
    # Never fail silently: if the base handler is not where we expect it, say so
    # in the job result rather than returning an empty success.
    return {
        "error": f"the ComfyUI handler was not found at {BASE_HANDLER}; "
                 "set COMFY_HANDLER_PATH to its location"
    }


if __name__ == "__main__":
    handler = _load_base_handler() or _missing
    runpod.serverless.start({"handler": handler})
