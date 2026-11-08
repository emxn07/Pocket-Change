"""Read aloud using the operating system's speech engine.

Each utterance runs in a separate process, so speech never blocks the game
and can be stopped or replayed at any time.
  Windows: built-in System.Speech via PowerShell
  macOS:   `say`
  Linux:   espeak-ng, espeak or spd-say (install one, e.g. `sudo pacman -S espeak-ng`)
"""
import platform
import re
import shutil
import subprocess


# Speech speed per engine for Slow / Normal / Fast
RATES = {
    "powershell": [-3, 0, 3],          # SAPI rate, -10..10
    "say": [140, 185, 240],            # words per minute
    "spd-say": [-40, 0, 40],           # -100..100
    "espeak": [120, 155, 200],         # words per minute (espeak and espeak-ng)
}


def _clean(text):
    text = re.sub(r"£(\d+)", r"\1 pounds", text)
    text = text.replace("£", " pounds ")
    text = text.replace("−", " minus ").replace("×", " times ").replace("→", " becomes ")
    text = text.replace("%", " percent")
    return re.sub(r"\s+", " ", text).strip()


class Speaker:
    def __init__(self):
        self.proc = None
        self.backend = self._detect()

    @staticmethod
    def _detect():
        system = platform.system()
        if system == "Windows":
            return "powershell" if shutil.which("powershell") else None
        if system == "Darwin":
            return "say" if shutil.which("say") else None
        for exe in ("espeak-ng", "espeak", "spd-say"):
            if shutil.which(exe):
                return exe
        return None

    @property
    def available(self):
        return self.backend is not None

    @property
    def description(self):
        names = {"powershell": "Windows speech", "say": "macOS speech", "espeak-ng": "eSpeak NG",
                 "espeak": "eSpeak", "spd-say": "Speech Dispatcher"}
        return names.get(self.backend, "No speech engine found")

    @property
    def speaking(self):
        return self.proc is not None and self.proc.poll() is None

    def speak(self, text, rate=1):
        self.stop()
        text = _clean(text)
        if not self.backend or not text:
            return False
        key = "espeak" if self.backend in ("espeak", "espeak-ng") else self.backend
        speed = RATES[key][max(0, min(2, rate))]
        try:
            if self.backend == "powershell":
                script = ("Add-Type -AssemblyName System.Speech; "
                          "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                          f"$s.Rate = {speed}; "
                          "$s.Speak([Console]::In.ReadToEnd())")
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                self.proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", script],
                                             stdin=subprocess.PIPE, creationflags=flags)
                self.proc.stdin.write(text.encode("ascii", "ignore"))
                self.proc.stdin.close()
            elif self.backend == "spd-say":
                self.proc = subprocess.Popen(["spd-say", "-w", "-r", str(speed), text])
            elif self.backend == "say":
                self.proc = subprocess.Popen(["say", "-r", str(speed), text])
            else:
                self.proc = subprocess.Popen([self.backend, "-s", str(speed), text],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            self.proc = None
            return False

    def stop(self):
        if self.speaking:
            try:
                self.proc.terminate()
            except OSError:
                pass
        if self.backend == "spd-say":
            subprocess.Popen(["spd-say", "-C"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.proc = None
