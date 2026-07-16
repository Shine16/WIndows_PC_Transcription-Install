import subprocess, threading, os
import tkinter as tk
from tkinter import filedialog, scrolledtext

DISTRO   = "Ubuntu-24.04"
WHISPERX = "~/whisperx/bin/whisperx"
HF_TOKEN = "hf_YOUR_TOKEN_HERE"
MEDIA    = (".mp3", ".mp4", ".m4a", ".wav", ".mkv", ".mov", ".aac", ".flac", ".ogg", ".webm")

stop_requested = False

def to_wsl(p):
    return "/mnt/" + p[0].lower() + p[2:].replace("\\", "/")

def log_line(text):
    log.insert(tk.END, text); log.see(tk.END)

def request_stop():
    global stop_requested
    stop_requested = True
    log_line("\n>>> Stop requested - will finish the current file, then stop.\n")

def run():
    global stop_requested
    folder = filedialog.askdirectory(title="Pick folder of audio/video files")
    if not folder:
        return
    folder = os.path.normpath(folder)
    stop_requested = False
    btn.config(state="disabled"); stop_btn.config(state="normal")

    def job():
        global stop_requested
        tdir = os.path.join(folder, "transcript")
        ddir = os.path.join(folder, "transcribed")
        os.makedirs(tdir, exist_ok=True)
        os.makedirs(ddir, exist_ok=True)

        files = sorted(f for f in os.listdir(folder)
                       if f.lower().endswith(MEDIA)
                       and os.path.isfile(os.path.join(folder, f)))
        if not files:
            log_line("No media files found in this folder (already all done?).\n")
        log_line(f"{len(files)} file(s) to transcribe.\n\n")

        done_count = 0
        for idx, fname in enumerate(files, 1):
            if stop_requested:
                break
            src  = os.path.join(folder, fname)
            name = os.path.splitext(fname)[0]
            log_line(f"=== [{idx}/{len(files)}] {fname} ===\n")

            opts = (f'--model large-v3 --language en '
                    f'--compute_type float16 --batch_size 4 '
                    f'--output_dir "{to_wsl(tdir)}"')
            if diarize_var.get():
                opts += f' --diarize --hf_token {HF_TOKEN}'
                n = speakers_var.get().strip()
                if n.isdigit() and int(n) > 0:
                    opts += f' --min_speakers {n} --max_speakers {n}'

            cmd = ["wsl.exe", "-d", DISTRO, "-e", "bash", "-lc",
                   f'{WHISPERX} "{to_wsl(src)}" {opts}']
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                log_line(line)
            p.wait()

            raw = os.path.join(tdir, name + ".txt")
            if p.returncode == 0 and os.path.exists(raw):
                new = os.path.join(tdir, name + "_transcript.txt")
                if os.path.exists(new):
                    os.remove(new)
                os.rename(raw, new)
                for ext in (".srt", ".vtt", ".json", ".tsv"):
                    extra = os.path.join(tdir, name + ext)
                    if os.path.exists(extra):
                        os.remove(extra)
                dest = os.path.join(ddir, fname)
                if os.path.exists(dest):
                    os.remove(dest)
                os.replace(src, dest)          # move original only AFTER success
                done_count += 1
                log_line(f"OK -> transcript\\{name}_transcript.txt\n\n")
            else:
                log_line(f"FAILED: {fname} left in place - will retry on next run.\n\n")

        if stop_requested:
            log_line(f"Stopped. {done_count} file(s) completed this session. "
                     f"Run again on the same folder to continue.\n")
        else:
            log_line(f"All done. {done_count} file(s) transcribed.\n")
        btn.config(state="normal"); stop_btn.config(state="disabled")

    threading.Thread(target=job, daemon=True).start()

root = tk.Tk(); root.title("WSL Batch Transcriber"); root.geometry("750x520")

controls = tk.Frame(root); controls.pack(pady=8)
diarize_var = tk.BooleanVar(value=False)
tk.Checkbutton(controls, text="Speaker labels (diarize)",
               variable=diarize_var, font=("Segoe UI", 11)).pack(side="left", padx=8)
tk.Label(controls, text="Speakers:", font=("Segoe UI", 11)).pack(side="left")
speakers_var = tk.StringVar(value="")
tk.Entry(controls, textvariable=speakers_var, width=4,
         font=("Segoe UI", 11)).pack(side="left", padx=4)

btnrow = tk.Frame(root); btnrow.pack(pady=4)
btn = tk.Button(btnrow, text="Choose folder and transcribe all",
                font=("Segoe UI", 12), command=run)
btn.pack(side="left", padx=6)
stop_btn = tk.Button(btnrow, text="Stop after current file",
                     font=("Segoe UI", 12), command=request_stop, state="disabled")
stop_btn.pack(side="left", padx=6)

log = scrolledtext.ScrolledText(root, font=("Consolas", 9))
log.pack(fill="both", expand=True, padx=8, pady=8)
root.mainloop()