#!/usr/bin/env bash
# Fetch the models when the worker starts, not when the image is built.
#
# Baking 54 GB into the image works but cannot be shipped: RunPod's builder
# caps a build at 30 minutes, and exporting plus sending an image that size
# took 20 of them on its own. The downloads themselves are the cheap part —
# the build log measured 21 GB in 78 s and 27 GB in 102 s, about 270 MB/s.
#
# Each file is skipped if it is already present, so a worker that FlashBoot
# restores, or one that handled a job earlier, starts immediately.
set -euo pipefail

REPO="${MODEL_REPO:-Comfy-Org/MiniMax-H3}"
DEST="${COMFY_MODEL_DIR:-/comfyui/models}"

files=(
  "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"
  "text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors"
  "vae/minimax_h3_video_vae_fp16.safetensors"
  "vae/minimax_h3_audio_vae_fp32.safetensors"
  "loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"
)

export HF_HUB_ENABLE_HF_TRANSFER=1
start=$(date +%s)
for f in "${files[@]}"; do
  if [ -s "$DEST/$f" ]; then
    echo "models: $f already here"
    continue
  fi
  echo "models: fetching $f"
  hf download "$REPO" "$f" --local-dir "$DEST"
done
echo "models: ready in $(( $(date +%s) - start ))s"
