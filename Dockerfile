# MiniMax H3 "anime" workflow as a RunPod serverless endpoint.
#
# The models are pulled from Hugging Face during the BUILD, on RunPod's
# builders, where the pull runs at roughly 1 GB/s. Nothing is uploaded from
# home: a 54 GB image over a 1.4 MB/s domestic uplink would take eleven hours.
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

ARG REPO=Comfy-Org/MiniMax-H3

# One RUN per file: a failed 27 GB download then costs only itself on a rebuild.
RUN hf download $REPO diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors \
      --local-dir /comfyui/models && \
    mv /comfyui/models/diffusion_models/*.safetensors /comfyui/models/diffusion_models/ || true

RUN hf download $REPO text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors \
      --local-dir /comfyui/models

RUN hf download $REPO vae/minimax_h3_video_vae_fp16.safetensors --local-dir /comfyui/models
RUN hf download $REPO vae/minimax_h3_audio_vae_fp32.safetensors --local-dir /comfyui/models

# The 4-step turbo LoRA. The local box uses a pruned build that is not on the
# Hub; this is Comfy-Org's official ref2v 4-step, same purpose.
RUN hf download $REPO loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors \
      --local-dir /comfyui/models

# ffmpeg is what SaveVideo and LoadVideo shell out to.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN ls -la /comfyui/models/diffusion_models /comfyui/models/text_encoders /comfyui/models/vae /comfyui/models/loras
