# Parakeet + pyannote on Windows: Complete Setup Guide

Transcribe long audio/video files with NVIDIA Parakeet and label who is speaking with pyannote — all running locally on your Windows PC with an NVIDIA GPU.

**What you need before starting:**
- Windows 10 or 11 (64-bit)
- An NVIDIA GPU (RTX 20-series or newer recommended, 12 GB VRAM ideal)
- Roughly 30 GB of free disk space (models + libraries)
- A free Hugging Face account (created in Step 6)
- Patience: the downloads total several GB

---

## Understanding the two windows (read this first)

You will work in **two different terminal windows** during this guide. Mixing them up is the #1 source of confusion:

| Window | How to open it | What runs there |
|---|---|---|
| **PowerShell** (Windows) | Start menu → type "PowerShell" | All `wsl ...` commands |
| **Ubuntu** (Linux) | Start menu → type "Ubuntu" | Everything else: `sudo`, `pip`, `python`, `ffmpeg`, `ls`, `cd` |

If you type a `wsl` command in Ubuntu, you'll get *"Command 'wsl' not found"*. If you type a Linux command in PowerShell, you'll get *"not recognized as the name of a cmdlet"*. Both errors just mean: switch to the other window.

**Basic Linux commands you'll use:**
- `cd foldername` — go into a folder. `cd ~` goes to your Linux home folder.
- `ls` — list files in the current folder.
- `nano filename` — open a simple text editor. Save with **Ctrl+O** then Enter; exit with **Ctrl+X**.
- Your Windows files are visible inside Ubuntu under `/mnt/c/...` — e.g. your Downloads folder is `/mnt/c/Users/YOURNAME/Downloads`.

---

## Step 1 — Update your NVIDIA driver (Windows)

Do this **first**. An old driver causes confusing GPU errors later.

1. Download the latest driver for your GPU from nvidia.com/Download (or use the NVIDIA App if installed). Either **Game Ready** or **Studio** works; Studio is slightly preferred for AI workloads.
2. Run the installer. Choose **Custom (Advanced)** → tick **"Perform a clean installation"**.
3. **Restart Windows** (a real restart, not just closing the installer).

> Important: never install an NVIDIA driver *inside* Ubuntu/WSL. The Windows driver covers WSL automatically.

## Step 2 — Install WSL2 with Ubuntu 24.04 (PowerShell)

WSL lets Windows run Linux. We specifically want **Ubuntu 24.04 LTS** because it ships Python 3.12, which the AI libraries support. Newer Ubuntu versions ship Python 3.14, which **breaks the install** — do not use the default `wsl --install` without naming the version.

1. Open **PowerShell** and run:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
2. Restart Windows if asked.
3. Open **Ubuntu 24.04** from the Start menu. On first launch it asks you to create a Linux username and password. The password won't show as you type — that's normal. Remember it: it's what you type whenever you use `sudo`.
4. Verify the Python version (in the Ubuntu window):
   ```bash
   python3 --version
   ```
   You want **3.12.x**. If you see 3.13 or 3.14, you installed the wrong Ubuntu — remove it from PowerShell with `wsl --unregister <name>` (find the name via `wsl --list --verbose`) and redo this step with `-d Ubuntu-24.04`.
5. Update WSL itself (PowerShell):
   ```powershell
   wsl --update
   ```

## Step 3 — Install the system tools (Ubuntu)

In the **Ubuntu** window:

```bash
sudo apt update
sudo apt install -y build-essential python3-dev python3-venv ffmpeg
```

Type your Linux password when asked.

> **If you get "Could not get lock /var/lib/apt/lists/lock":** Ubuntu is running an automatic update in the background. Wait 2–3 minutes and try again. Do NOT delete the lock file. If it persists, close Ubuntu, run `wsl --shutdown` in PowerShell, wait 15 seconds, reopen Ubuntu, and retry.

Then check the GPU is visible from inside Ubuntu:

```bash
nvidia-smi
```

You should see your GPU listed with a driver version. If this errors, redo Step 1 (clean driver install + Windows restart).

## Step 4 — Create the Python environment and install NeMo (Ubuntu)

A "venv" is an isolated box for Python libraries so different projects don't break each other.

```bash
python3 -m venv ~/nemo
source ~/nemo/bin/activate
pip install -U pip setuptools wheel
```

Your prompt now starts with `(nemo)`. **Every time you open a new Ubuntu window, run `source ~/nemo/bin/activate` again before doing anything** — this is the single most-forgotten step.

Now install NeMo. The download is several GB and unstable connections often break mid-way, so use this self-retrying command — it keeps restarting automatically until it succeeds, resuming from what's already downloaded:

```bash
until pip install "nemo_toolkit[asr]" --timeout 1000 --retries 10; do echo "---- dropped, retrying ----"; sleep 5; done
```

Leave it running (can take a long time on slow connections — each retry makes progress). Success looks like a long `Successfully installed nemo_toolkit-... torch-...` line.

Verify:

```bash
python -c "import nemo.collections.asr as x; print('nemo ok')"
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

You want `nemo ok`, a torch version, and `True`. Ignore harmless startup messages about "OneLogger", "telemetry", or "Megatron" — they appear on every run and mean nothing.

> **If `torch.cuda.is_available()` prints `False`** with a warning that your driver is "too old": your Windows driver doesn't support the CUDA version torch was built for. Either update the driver (Step 1) or install a torch built for an older CUDA:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu126 --timeout 1000 --retries 10
> ```
> Then run `wsl --shutdown` in PowerShell, reopen Ubuntu, reactivate the venv, and re-check.

## Step 5 — Install pyannote in the same environment (Ubuntu)

```bash
source ~/nemo/bin/activate
until pip install pyannote.audio --timeout 1000 --retries 10; do echo "---- retrying ----"; sleep 5; done
```

**Watch the output:** pip may upgrade torch to satisfy pyannote. That's usually fine, but note what version you end up with:

```bash
python -c "import torch; print(torch.__version__)"
python -c "import pyannote.audio; print('pyannote ok')"
python -c "import nemo.collections.asr; print('nemo ok')"
```

All three should succeed. Keep the torch version in mind — if you later hit the "device not ready" error (see Troubleshooting), the fix involves torch.

## Step 6 — Hugging Face account, token, and license (web browser)

The diarization model is free but requires accepting a license:

1. Create a free account at **huggingface.co**.
2. Go to **Settings → Access Tokens → Create new token**, type **Read**. Copy the token (starts with `hf_`). Keep it private.
3. Visit the model page for **pyannote/speaker-diarization-community-1** on Hugging Face and **accept the user agreement** — using the *same account* the token belongs to.

> Common trap: older tutorials tell you to accept the license for `speaker-diarization-3.1`. That's the wrong model — if you accept only that one, diarization silently produces empty speaker labels. Accept **community-1**.

## Step 7 — Create the transcription + diarization script (Ubuntu)

Go to the folder where your audio lives (example uses Downloads):

```bash
cd /mnt/c/Users/YOURNAME/Downloads
nano transcribe_diarize.py
```

Paste the following, then edit the settings block at the top (file name, token, speaker count). Save with **Ctrl+O**, Enter, exit with **Ctrl+X**.

```python
import os
os.environ["CUDA_MODULE_LOADING"] = "EAGER"
import glob, json, subprocess, gc
import torch
import nemo.collections.asr as nemo_asr
from pyannote.audio import Pipeline

# ---- settings: edit these ----
INPUT         = "myaudio.wav"        # your 16kHz mono wav (see Step 8)
HF_TOKEN      = "hf_YOUR_TOKEN_HERE" # your Hugging Face read token
NUM_SPEAKERS  = None                 # set a number if known, e.g. 2
OUT_TXT       = "transcript_diarized.txt"
# ---- advanced (usually leave alone) ----
CHUNK_DIR     = "chunks120"
CHUNK_SECONDS = 120                  # 2-min chunks: safe for 12GB VRAM
PROGRESS      = "progress.json"
# --------------------------------

# Stage 1: split audio into small chunks (GPU memory limit)
os.makedirs(CHUNK_DIR, exist_ok=True)
if not glob.glob(f"{CHUNK_DIR}/chunk_*.wav"):
    print("Splitting audio...")
    subprocess.run(["ffmpeg","-y","-i",INPUT,"-f","segment",
                    "-segment_time",str(CHUNK_SECONDS),
                    "-ar","16000","-ac","1","-c:a","pcm_s16le",
                    f"{CHUNK_DIR}/chunk_%03d.wav"], check=True)

# Stage 2: Parakeet transcription with timestamps (resumable)
done = json.load(open(PROGRESS)) if os.path.exists(PROGRESS) else {}
chunks = sorted(glob.glob(f"{CHUNK_DIR}/chunk_*.wav"))

if any(c not in done for c in chunks):
    model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v2")
    for i, c in enumerate(chunks):
        if c in done:
            continue
        offset = i * CHUNK_SECONDS
        print(f"Transcribing chunk {i+1}/{len(chunks)}")
        out = model.transcribe([c], timestamps=True, num_workers=0)
        segs = []
        for seg in out[0].timestamp['segment']:
            text = seg.get('segment', seg.get('text', '')).strip()
            segs.append({"start": seg['start']+offset,
                         "end":   seg['end']+offset, "text": text})
        done[c] = segs
        json.dump(done, open(PROGRESS, "w"))   # saved after every chunk
    del model; gc.collect(); torch.cuda.empty_cache()
else:
    print("Transcription already complete, skipping to diarization")

segments = []
for c in chunks:
    segments.extend(done.get(c, []))

# Stage 3: pyannote speaker diarization
print("Diarizing (takes roughly as long as the audio itself)...")
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1", token=HF_TOKEN)
pipeline.to(torch.device("cuda"))
output = pipeline(INPUT, num_speakers=NUM_SPEAKERS) if NUM_SPEAKERS else pipeline(INPUT)

def extract_turns(output):
    turns = []
    try:
        for turn, speaker in output.exclusive_speaker_diarization:
            turns.append((turn.start, turn.end, speaker))
        if turns:
            return turns
    except AttributeError:
        pass
    diar = getattr(output, "speaker_diarization", output)
    for segment, _, speaker in diar.itertracks(yield_label=True):
        turns.append((segment.start, segment.end, speaker))
    return turns

spk_turns = extract_turns(output)
print(f"{len(spk_turns)} speaker turns found")

# Stage 4: merge speakers into the transcript by timestamp
def speaker_at(t):
    for s, e, spk in spk_turns:
        if s <= t <= e:
            return spk
    best, bestd = "UNKNOWN", 1e9
    for s, e, spk in spk_turns:
        d = min(abs(t-s), abs(t-e))
        if d < bestd:
            best, bestd = spk, d
    return best

for seg in segments:
    seg["speaker"] = speaker_at((seg["start"]+seg["end"])/2)

with open(OUT_TXT, "w") as f:
    current, line = None, ""
    for seg in segments:
        if seg["speaker"] != current:
            if line: f.write(line + "\n\n")
            line, current = f'{seg["speaker"]}: {seg["text"]}', seg["speaker"]
        else:
            line += " " + seg["text"]
    if line: f.write(line + "\n")
print(f"Done -> {OUT_TXT}")
```

## Step 8 — Prepare your audio and run

Parakeet needs **16 kHz mono WAV**. Convert any audio or video file (mp4, mp3, m4a, mov...) with one command — run it in the folder your file is in:

```bash
ffmpeg -i "myvideo.mp4" -ar 16000 -ac 1 myaudio.wav
```

(Keep the quotes if the filename has spaces. The name after `-i` must match your real file — use `ls` to check what's there.)

Then run the pipeline:

```bash
source ~/nemo/bin/activate     # if not already active
python transcribe_diarize.py
```

**What to expect:**
- **First run only:** it downloads the Parakeet model (~2.5 GB) and the diarization models. These are cached forever after.
- Transcription prints `Transcribing chunk 1/115...` and marches through. It saves progress after every chunk — if it's interrupted for any reason, just run the same command again and it resumes where it stopped.
- Diarization is the slow stage: on long recordings it takes roughly as long as the audio itself. Messages about "Lightning upgraded your checkpoint" and "TF32 disabled" are harmless.
- The result is a text file with speaker-labelled blocks:

```
SPEAKER_00: so how did you get into trading?

SPEAKER_01: honestly it started during covid...
```

Find-and-replace `SPEAKER_00` / `SPEAKER_01` with real names once you know who's who.

**For each new recording:** convert with ffmpeg, edit `INPUT` and `OUT_TXT` at the top of the script (and delete the old `chunks120` folder and `progress.json`, or change those names too), then run again.

---

## Troubleshooting

**"Command 'wsl' not found" inside Ubuntu** — `wsl` commands belong in PowerShell. Switch windows.

**"source: not recognized" in PowerShell** — Linux commands belong in Ubuntu. Switch windows.

**"No module named 'nemo'"** — the venv isn't active. Run `source ~/nemo/bin/activate` (your prompt should show `(nemo)`).

**"can't open file ... No such file or directory"** — you're in the wrong folder. `cd` to where the script/audio actually is; use `ls` to look around.

**Downloads keep breaking ("IncompleteRead" / "Connection broken")** — normal on unstable connections. Use the `until pip install ...; do ...; done` retry-loop form shown above; every completed file is cached, so each retry makes progress.

**pip tries to compile and fails with "Unknown compiler(s)"** — you're missing build tools (`sudo apt install -y build-essential python3-dev`) or, more likely, you're on the wrong Python version (3.13/3.14) and pip can't find prebuilt packages. Check `python3 --version`; if it isn't 3.12, reinstall Ubuntu-24.04 (Step 2).

**`torch.cuda.is_available()` is False, "driver too old"** — update the Windows NVIDIA driver (Step 1), restart Windows, run `wsl --shutdown` in PowerShell, reopen Ubuntu.

**"RuntimeError: CUDA driver error: device not ready" during transcription** — two known causes, in order of likelihood:
1. *Chunks too long for your GPU memory* (this can masquerade as a driver error on WSL). The script already uses safe 120-second chunks; if you changed `CHUNK_SECONDS` upward, put it back to 120 (or lower to 60 on GPUs with less than 12 GB).
2. *Torch version incompatibility on WSL.* Install an older, stable torch:
   ```bash
   pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124 --timeout 1000 --retries 10
   ```
   Then `wsl --shutdown` (PowerShell), reopen, and retry.

**Transcription hangs at "Transcribing: 0it"** — usually the model is still downloading (first run) or the audio file is missing/empty. Check the file exists with `ls -lh yourfile.wav`, and watch the model cache grow with `du -sh ~/.cache/huggingface`.

**Diarization gives empty/blank speaker labels** — you accepted the license for the wrong model. Accept **speaker-diarization-community-1** on Hugging Face with the same account as your token (Step 6).

**GPU acting strangely after several runs** — WSL's GPU layer occasionally needs a reset: `wsl --shutdown` in PowerShell, wait 15 seconds, reopen Ubuntu.

---

## Quick reference card

```bash
# every new Ubuntu window:
source ~/nemo/bin/activate

# convert any media file to what Parakeet needs:
ffmpeg -i "input.mp4" -ar 16000 -ac 1 audio.wav

# run the full pipeline (resumes automatically if interrupted):
python transcribe_diarize.py

# reset WSL/GPU (PowerShell, Windows side):
wsl --shutdown
```
