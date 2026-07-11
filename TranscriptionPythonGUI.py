#running on Python 3.12 (64-bit)
#if tkinter is not installed, use "pip install tk" in command line

import subprocess, threading, os
import tkinter as tk
from tkinter import filedialog, scrolledtext

DISTRO   = "Ubuntu-24.04"
WHISPERX = "~/whisperx/bin/whisperx"
HF_TOKEN = "hf_-----------------------"   # needed only when diarize is ticked

def to_wsl(p):
    return "/mnt/" + p[0].lower() + p[2:].replace("\\", "/")

def run():
    f = filedialog.askopenfilename(title="Pick audio/video",
        filetypes=[("Media", "*.mp3 *.mp4 *.m4a *.wav *.mkv *.mov")])
    if not f:
        return
    btn.config(state="disabled")
    log.insert(tk.END, f"Transcribing: {f}\n"); log.see(tk.END)

    def job():
        src_dir_win = os.path.dirname(f)
        src_dir_wsl = to_wsl(src_dir_win)
        name = os.path.splitext(os.path.basename(f))[0]

        opts = (f'--model large-v3 --language en '
                f'--compute_type float16 --batch_size 4 '
                f'--output_dir "{src_dir_wsl}"')
        if diarize_var.get():
            opts += f' --diarize --hf_token {HF_TOKEN}'
            n = speakers_var.get().strip()
            if n.isdigit() and int(n) > 0:
                opts += f' --min_speakers {n} --max_speakers {n}'

        cmd = ["wsl.exe", "-d", DISTRO, "-e", "bash", "-lc",
               f'{WHISPERX} "{to_wsl(f)}" {opts}']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        for line in p.stdout:
            log.insert(tk.END, line); log.see(tk.END)
        p.wait()

        old = os.path.join(src_dir_win, name + ".txt")
        new = os.path.join(src_dir_win, name + "_transcript.txt")
        if os.path.exists(old):
            if os.path.exists(new):
                os.remove(new)
            os.rename(old, new)
            for ext in (".srt", ".vtt", ".json", ".tsv"):
                extra = os.path.join(src_dir_win, name + ext)
                if os.path.exists(extra):
                    os.remove(extra)
            log.insert(tk.END, f"\nDONE -> {new}\n\n")
        else:
            log.insert(tk.END, "\nERROR: transcript not found - check log above.\n\n")
        log.see(tk.END)
        btn.config(state="normal")

    threading.Thread(target=job, daemon=True).start()

root = tk.Tk(); root.title("WSL Transcriber"); root.geometry("700x500")

controls = tk.Frame(root); controls.pack(pady=8)
diarize_var = tk.BooleanVar(value=False)
tk.Checkbutton(controls, text="Speaker labels (diarize)",
               variable=diarize_var, font=("Segoe UI", 11)).pack(side="left", padx=8)
tk.Label(controls, text="Speakers:", font=("Segoe UI", 11)).pack(side="left")
speakers_var = tk.StringVar(value="")
tk.Entry(controls, textvariable=speakers_var, width=4,
         font=("Segoe UI", 11)).pack(side="left", padx=4)

btn = tk.Button(root, text="Choose file and transcribe",
                font=("Segoe UI", 12), command=run)
btn.pack(pady=4)
log = scrolledtext.ScrolledText(root, font=("Consolas", 9))
log.pack(fill="both", expand=True, padx=8, pady=8)
root.mainloop()
