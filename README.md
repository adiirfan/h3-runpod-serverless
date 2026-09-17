# MiniMax H3 on RunPod serverless

Stock ComfyUI plus the MiniMax H3 models, as a serverless endpoint.

Build this repo from the RunPod console (Serverless -> New Endpoint -> GitHub).
The build pulls ~56 GB from Hugging Face on RunPod's side; expect the first
build to take a while and later ones to reuse the layers.

Send a job as `{"input": {"workflow": <the exported API workflow>, "images":
[{"name": "character.png", "image": "<base64>"}]}}`.

`workflow_anime.json` is the graph, with every custom node removed so no extra
packs are needed. Set the reference clip and character image names to match the
files you upload with the request.
