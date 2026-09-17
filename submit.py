"""Send one anime render to the RunPod endpoint and wait for it.

Inputs travel inside the request: the character picture and the reference clip
are base64-encoded and uploaded to the worker's ComfyUI input folder under the
names the workflow expects. The finished video comes back the same way.
"""
import argparse, base64, json, os, sys, time, urllib.request

ENDPOINT = os.environ.get("RUNPOD_ENDPOINT", "y8s9armmpz84of")
KEY = open(os.path.expanduser("~/.config/runpod/api_key")).read().strip()
API = f"https://api.runpod.ai/v2/{ENDPOINT}"
HDRS = {"Content-Type": "application/json", "Authorization": "Bearer " + KEY}


def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def call(path, body=None):
    req = urllib.request.Request(API + path, data=(json.dumps(body).encode() if body else None),
                                 headers=HDRS, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="/home/debian/ComfyUI/input/H3_Edit_00308.png")
    ap.add_argument("--video", default="/home/debian/ComfyUI/input/split_shot1.mp4")
    ap.add_argument("--prompt-file", default="/home/debian/runpod-h3/prompt_example.txt")
    ap.add_argument("--seconds", type=float, default=3.962)
    ap.add_argument("--seed", type=int, default=973103107)
    ap.add_argument("--out", default="/home/debian/runpod-h3/runpod_output.mp4")
    a = ap.parse_args()

    wf = json.load(open("/home/debian/runpod-h3/workflow_anime.json"))
    wf["143"]["inputs"]["image"] = "character.png"
    wf["149"]["inputs"]["file"] = "reference.mp4"
    wf["132"]["inputs"]["value"] = a.seconds
    wf["159"]["inputs"]["duration"] = a.seconds
    wf["129"]["inputs"]["noise_seed"] = a.seed
    wf["138"]["inputs"]["value"] = open(a.prompt_file).read()

    payload = {"input": {"workflow": wf, "images": [
        {"name": "character.png", "image": b64(a.image)},
        {"name": "reference.mp4", "image": b64(a.video)},
    ]}}
    size = len(json.dumps(payload))
    print(f"request is {size/1e6:.1f} MB (the /run limit is 10 MB)", flush=True)

    t0 = time.time()
    job = call("/run", payload)
    jid = job.get("id")
    print("job", jid, "status", job.get("status"), flush=True)

    last = None
    while True:
        st = call(f"/status/{jid}")
        s = st.get("status")
        if s != last:
            print(f"{time.time()-t0:6.0f}s  {s}"
                  + (f"  delayTime={st.get('delayTime')}ms executionTime={st.get('executionTime')}ms"
                     if s in ("COMPLETED", "FAILED") else ""), flush=True)
            last = s
        if s in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
            break
        time.sleep(5)

    out = st.get("output") or {}
    if isinstance(out, dict):
        for v in out.get("videos", []):
            if v.get("data"):
                open(a.out, "wb").write(base64.b64decode(v["data"]))
                print(f"saved {a.out} ({v['bytes']/1e6:.2f} MB) from {v['filename']}")
            else:
                print("video not returned:", json.dumps(v)[:200])
        if out.get("errors"):
            print("errors:", json.dumps(out["errors"])[:400])
        if not out.get("videos"):
            print("no video in the response; keys were:", list(out))
    else:
        print("unexpected output:", json.dumps(out)[:300])
    print("total wall time: %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
