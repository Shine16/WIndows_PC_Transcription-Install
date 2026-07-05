# WhisperX on Windows — Beginner Install Guide

A complete beginner's guide: install WSL2 and WhisperX from scratch and turn any audio or video file into a text transcript — with optional speaker labels — on your own PC. No Linux or Python experience needed.

---

## What you will build

By the end of this guide, your Windows PC will transcribe audio and video files (even hours-long recordings) into accurate text, with timestamps, using the Whisper AI model. Optionally, it can also label who said what (`SPEAKER_00:`, `SPEAKER_01:`...). Everything runs locally on your own graphics card — nothing is uploaded anywhere, and nothing costs money.

WhisperX is a free tool that wraps OpenAI's Whisper model and adds fast processing, precise word timestamps, and speaker labelling — all in one command.

### What you need before starting

- A Windows 10 or Windows 11 PC with an **NVIDIA graphics card** (8 GB+ of video memory recommended; this guide was written on an RTX 3060 12 GB).
- About **15 GB of free disk space** (the Linux system, Python packages, and AI models).
- A reasonably stable internet connection. Total downloads are several gigabytes. If your connection drops often, this guide includes commands that retry automatically.
- Optional, only for speaker labels: a free account at **huggingface.co** (Part 7).

### The two windows you will use

You will type commands into two different apps, and it matters which one you use:

- **PowerShell** (blue window) — Windows' own command window. Open it by pressing Start, typing `powershell`, and clicking it. Used only for commands starting with `wsl`.
- **Ubuntu** (black window) — the Linux system you are about to install. Open it from the Start menu after Part 1. Used for everything else: `sudo`, `pip`, `whisperx`, `ffmpeg`, `ls`, `cd`.

How to know when a command finished: a new line appears ending in `$`, waiting for you. To type, click inside the window first. To paste into Ubuntu, right-click.

> **Note:** If you type `wsl --shutdown` and see "Command 'wsl' not found", you are in the Ubuntu window by mistake — switch to PowerShell. If `source` or `sudo` is "not recognized", you are in PowerShell — switch to Ubuntu.

---

## Part 1 — Install WSL2 with Ubuntu 24.04

WSL (Windows Subsystem for Linux) runs a real Linux system inside Windows — the AI tools in this guide are far more reliable on Linux. The Ubuntu **version matters**: 24.04 ships Python 3.12, which WhisperX supports. The very newest Ubuntu versions ship Python 3.14, which breaks the install with confusing compiler errors — so we install 24.04 specifically.

### Step 1.1 — Install Ubuntu 24.04

In **PowerShell**:

```powershell
wsl --install -d Ubuntu-24.04
```

Let it download and install (a few minutes). **Restart your PC** if it asks. Ubuntu then opens on its own, or you can open it any time from the Start menu (type "Ubuntu").

### Step 1.2 — Create your Linux username and password

On first launch, Ubuntu asks you to create a username and password. This is separate from your Windows login. **While typing the password nothing appears on screen — that is normal.** Type it and press Enter. You will need this password whenever a command starts with `sudo`.

### Step 1.3 — Verify the right version installed

In **PowerShell**:

```powershell
wsl --list --verbose
```

You should see **Ubuntu-24.04** with VERSION 2. Then check Python — in the **Ubuntu** window:

```bash
python3 --version
```

It must say **Python 3.12.x**. If it says 3.14, a newer Ubuntu was installed by mistake — remove it (`wsl --unregister <name>` in PowerShell) and redo Step 1.1 making sure to include `-d Ubuntu-24.04`.

> **Note:** Good to know: your Windows files are visible inside Ubuntu under `/mnt/c/` — for example your Downloads folder is `/mnt/c/Users/<YourName>/Downloads`. That is how Ubuntu will read your recordings and where it will save transcripts.

---

## Part 2 — NVIDIA driver on Windows

Inside WSL, the graphics driver comes from **Windows** — never install a Linux NVIDIA driver inside Ubuntu. You only need the Windows driver to be recent, because old drivers cannot run the AI libraries.

### Step 2.1 — Update the driver

Open the **NVIDIA App** (or GeForce Experience) on Windows and update to the latest driver — Game Ready or Studio both work; Studio is a good default for AI work. Alternatively download it from nvidia.com/Download (choose your card model). Then **restart Windows**.

### Step 2.2 — Verify Ubuntu can see the graphics card

In **Ubuntu**:

```bash
nvidia-smi
```

You should see a table naming your graphics card, a driver version, and a "CUDA Version" in the top-right corner. If this command fails or hangs: rerun the NVIDIA installer on Windows, choose Custom → "Perform a clean installation", restart Windows, then in PowerShell run `wsl --shutdown`, wait 15 seconds and reopen Ubuntu.

---

## Part 3 — Prepare Ubuntu and create a Python environment

### Step 3.1 — Install the basic tools

This installs **ffmpeg** (the audio converter) and Python's environment tool. It asks for the password you created in Part 1.

In **Ubuntu**:

```bash
sudo apt update
sudo apt install -y python3-venv ffmpeg
```

> **Note:** If you see "Could not get lock /var/lib/apt/lists/lock", Ubuntu is busy updating itself in the background right after installation. Wait two minutes and try again. If it persists: close Ubuntu, run `wsl --shutdown` in PowerShell, wait 15 seconds, reopen Ubuntu.

### Step 3.2 — Create and activate a virtual environment

A virtual environment ("venv") is a private folder that holds all the Python packages for this project so nothing interferes with anything else on the system. We create one called **whisperx** and "activate" it — activating means your commands now use this private setup:

In **Ubuntu**:

```bash
python3 -m venv ~/whisperx
source ~/whisperx/bin/activate
pip install -U pip
```

After activating, every line in the window starts with `(whisperx)`. **This is the single most common beginner mistake:** every new Ubuntu window starts *deactivated*. If a later command says "whisperx: command not found" or "No module named ...", you almost certainly forgot to run `source ~/whisperx/bin/activate` first.

---

## Part 4 — Install WhisperX

This is the biggest download of the guide — several gigabytes, including the CUDA libraries that let the AI use your graphics card. The command below retries automatically if your connection drops; every finished file is cached, so each retry continues from where it stopped instead of starting over. Leave it running until you see a line starting with "Successfully installed".

In **Ubuntu** — venv active, prompt shows `(whisperx)`:

```bash
until pip install whisperx --timeout 1000 --retries 10; do echo "---- dropped, retrying ----"; sleep 5; done
```

> **Note:** Individual files here can be 500–700 MB (names like nvidia_cublas, nvidia_cudnn). A slow progress bar is not frozen — check the numbers and the ETA. If it dies mid-download, the loop restarts it automatically.

### Step 4.1 — Test that the graphics card works

In **Ubuntu**:

```bash
python -c "import torch; x=torch.randn(4,4).cuda(); print((x@x).sum())"
```

Success looks like `tensor(-3.1415, device='cuda:0')` — any number is fine; `device='cuda:0'` is the part that matters. It means the graphics card is ready. If this errors or hangs: run `wsl --shutdown` in PowerShell, wait 15 seconds, reopen Ubuntu, activate the venv, and try again.

---

## Part 5 — Prepare your audio file

WhisperX can read most formats, but the most reliable input is a 16 kHz, single-channel (mono) WAV file. One ffmpeg command converts anything — MP4 video, MP3, M4A — into exactly that. Work inside your Windows Downloads folder so files are easy to find from Windows:

In **Ubuntu**:

```bash
cd /mnt/c/Users/<YourName>/Downloads
ffmpeg -i "myrecording.mp4" -ar 16000 -ac 1 audio.wav
```

Replace `<YourName>` with your Windows username and `myrecording.mp4` with your real file name — keep the quotes, they matter if the name has spaces. Not sure of the exact name? Type `ls` to list what is in the folder.

---

## Part 6 — Transcribe (text only, no account needed)

This is the basic run — a full transcript with timestamps. No token, no account, nothing to sign up for:

In **Ubuntu** — venv active, in your Downloads folder:

```bash
whisperx audio.wav --model large-v3 --language en \
  --compute_type float16 --batch_size 4 --output_dir out
```

What the options mean:

- `--model large-v3` — the most accurate Whisper model (about 3 GB, downloaded once on the first run, then reused forever).
- `--language en` — skips language detection; change it (e.g. `zh`, `vi`) or remove it to auto-detect.
- `--compute_type float16 --batch_size 4` — settings that fit comfortably in 12 GB of video memory.
- `--output_dir out` — results are written into a folder called **out**: a .txt transcript, a .srt subtitle file, and more.

The first run pauses for a while at **model.bin** — that is the one-time 3 GB model download; the progress bar shows the percentage. After that, transcription itself is fast: a 1-hour recording typically takes only a few minutes on the graphics card.

> **Note:** If you get an "out of memory" error, lower the load: use `--batch_size 2`, and if that is not enough add `--compute_type int8` (slightly less accurate, half the memory).

---

## Part 7 — Optional: speaker labels (who said what)

WhisperX can also label each line with the speaker. The speaker-labelling model is free but "gated": you must accept its licence with a free Hugging Face account and prove it with a token (a long code starting with `hf_`). No payment is involved at any point.

### Step 7.1 — Account, token, licence

1. Create a free account at **huggingface.co**.
2. Go to **Settings → Access Tokens**, create a token of type **Read**, and copy it somewhere safe. It starts with `hf_`.
3. While logged in to that same account, open **huggingface.co/pyannote/speaker-diarization-community-1** and accept the user conditions.

> **Note:** It must be the **community-1** model page. Many older tutorials point to the previous model (speaker-diarization-3.1); accepting only that one makes the run finish with empty speaker labels and no error message.

### Step 7.2 — Run with speaker labels

In **Ubuntu**:

```bash
whisperx audio.wav --model large-v3 --language en \
  --compute_type float16 --batch_size 4 \
  --diarize --hf_token hf_YOUR_TOKEN_HERE \
  --min_speakers 2 --max_speakers 2 \
  --output_dir out
```

Paste your real token in place of `hf_YOUR_TOKEN_HERE`. If you know how many people are speaking, set `--min_speakers` and `--max_speakers` to that number — it noticeably improves accuracy. If you don't know, remove both options.

Be patient: speaker labelling is the slow stage. For long recordings it takes roughly as long as the audio itself. Messages about "Lightning", "TF32", "ReproducibilityWarning" or "telemetry" are normal noise — ignore them. The result in the **out** folder looks like:

```text
[SPEAKER_00]: so how did you get started with all of this?
[SPEAKER_01]: honestly it began a few years ago when I...
```

Rename SPEAKER_00 / SPEAKER_01 to real names afterwards with find & replace in any text editor.

---

## Part 8 — Everyday use afterwards

Nothing reinstalls and no models re-download — everything is cached. For each new recording, the whole routine is three commands:

In **Ubuntu**:

```bash
source ~/whisperx/bin/activate
cd /mnt/c/Users/<YourName>/Downloads
ffmpeg -i "newfile.mp4" -ar 16000 -ac 1 audio.wav
whisperx audio.wav --model large-v3 --language en --compute_type float16 --batch_size 4 --output_dir out
```

(Add the `--diarize` options from Part 7 when you want speaker labels.) Transcripts appear in the **out** folder inside Downloads — open them straight from Windows.

---

## Part 9 — Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Command 'wsl' not found" inside Ubuntu | wsl commands belong in PowerShell. Switch windows. |
| "whisperx: command not found" / "No module named ..." | Venv not active. Run: `source ~/whisperx/bin/activate` (prompt must show `(whisperx)`). |
| "can't open file ..." / "No such file or directory" | You are in the wrong folder, or the file name is different. `cd` to the right folder and type `ls` to see the real names. |
| pip download dies mid-file (IncompleteRead / Connection broken) | Flaky connection. The `until ... done` loop from Part 4 auto-retries; finished files are cached, so it always makes progress. |
| Install tries to compile / "Unknown compiler" errors | Wrong Python version (3.14). Use Ubuntu 24.04, which ships Python 3.12 (Part 1). |
| "The NVIDIA driver on your system is too old" | Update the Windows NVIDIA driver, restart Windows, then run `wsl --shutdown` in PowerShell and reopen Ubuntu. |
| GPU test fails or hangs | `wsl --shutdown` in PowerShell, wait 15 seconds, reopen Ubuntu, activate venv, retry. If it persists, do a clean driver reinstall (Part 2). |
| Stuck at "model.bin 0%" on first run | It is downloading the 3 GB Whisper model — watch the percentage. One time only; it is cached afterwards. |
| CUDA out of memory during transcription | Lower the load: `--batch_size 2`, then also `--compute_type int8` if needed. |
| Speaker labels are empty, but no error | Licence accepted for the wrong model. Accept it for **speaker-diarization-community-1**, logged in to the same account that made the token (Part 7). |
| Slow "Performing voice activity detection..." stage | Normal. Speaker labelling takes roughly as long as the audio itself on long files. Let it run. |
| apt: "Could not get lock" | Ubuntu is updating itself in the background. Wait two minutes; if stuck, `wsl --shutdown` in PowerShell and reopen. |
| Anything GPU-related acting strange | First move is always: `wsl --shutdown` in PowerShell, wait 15 s, reopen Ubuntu, reactivate the venv. |

---

## Quick reference — the golden rules

- `wsl` commands go in PowerShell; everything else goes in Ubuntu.
- Always activate first: `source ~/whisperx/bin/activate` in every new Ubuntu window.
- When downloads fail, just re-run the same command — progress is cached.
- When the GPU acts strange, `wsl --shutdown` (PowerShell), wait 15 s, reopen.
- First runs are slow (model downloads); every run after is fast.
