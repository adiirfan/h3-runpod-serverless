# MiniMax H3 "anime" workflow as a RunPod serverless endpoint.
#
# The models are pulled from Hugging Face when a WORKER STARTS, not at build
# time. Building them in works, but the resulting 56 GB image took 20 minutes to
# export and ship, and RunPod kills a build at 30. Fetching at start costs about
# four minutes on a genuinely new worker and nothing on a warm one.
#
# Everything in the workflow is stock ComfyUI. The three custom node packs the
# local copy uses are all droppable: the KJ preview node and its taeh3 model
# only draw a preview, the Spectrum node is disabled, and H3-Optimizations
# trades speed for VRAM, which a rented card does not need.
FROM runpod/worker-comfyui:5.10.0-base

# huggingface_hub gives resumable, parallel downloads; plain curl on a 27 GB
# file over a build that can retry is a bad trade.
RUN pip install --no-cache-dir "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# ffmpeg is what SaveVideo and LoadVideo shell out to.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install our handler in place of the base one, keeping the original beside it.
# start.sh runs `python -u /handler.py`, so ours has to sit at that exact path;
# it loads the original from COMFY_HANDLER_PATH and adds video output, which the
# base handler does not return at all.
RUN mv /handler.py /handler_base.py
COPY handler.py /handler.py
ENV COMFY_HANDLER_PATH=/handler_base.py
ENV COMFY_OUTPUT_DIR=/comfyui/output

# The models are fetched when a worker starts, so the image stays small enough
# to build and ship inside RunPod's 30-minute build limit.
COPY fetch_models.sh /fetch_models.sh
RUN chmod +x /fetch_models.sh

RUN python -c "compile(open('/handler.py').read(), '/handler.py', 'exec')" && \
    test -f /handler_base.py && test -x /fetch_models.sh && \
    bash -n /fetch_models.sh

CMD ["/bin/bash", "-c", "/fetch_models.sh && exec /start.sh"]
