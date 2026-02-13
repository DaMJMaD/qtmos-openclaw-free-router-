# tonesequencer.py

import time
from pathlib import Path

try:
    import winsound
except Exception:
    winsound = None


class ToneSequencer:
    def __init__(self, lexicon_file: str = "emotional_lexicon.txt"):
        self.tones = {}
        self._load(Path(lexicon_file))
        print(f"[VOICE]: Loaded {len(self.tones)} tones.")

    def _load(self, path: Path):
        if not path.exists():
            return

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", ";", "Code")):
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 4:
                    continue

                code = parts[0].upper()
                try:
                    pulse = int(parts[1])
                except Exception:
                    pulse = 100

                try:
                    freq = int(parts[2])
                except Exception:
                    freq = 440

                name = parts[3]
                color = parts[4] if len(parts) >= 5 else "#FFFFFF"

                self.tones[code] = {
                    "pulse": pulse,
                    "freq": freq,
                    "name": name,
                    "color": color,
                }

    def play_sequence(self, codes, loops=1, rest=50):
        for _ in range(loops):
            for code in codes:
                tone = self.tones.get(code)
                if not tone:
                    print(f"[TONE] Unknown: {code}")
                    continue

                freq = tone["freq"]
                dur = tone["pulse"]
                name = tone["name"]

                print(f"[TONE] {code}: {name} → {freq}Hz for {dur}ms")

                if winsound:
                    try:
                        winsound.Beep(freq, dur)
                    except Exception:
                        pass
                else:
                    time.sleep(dur / 1000)

            time.sleep(rest / 1000)

    @staticmethod
    def load_lexicon(filepath="emotional_lexicon.txt"):
        lex = {}
        path = Path(filepath)
        if not path.exists():
            return lex

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", ";")):
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 4:
                    continue

                symbol, freq, code, desc = parts[:4]
                try:
                    freq = float(freq)
                except ValueError:
                    freq = 440.0

                lex[symbol] = {
                    "freq": freq,
                    "code": code,
                    "desc": desc,
                }

        return lex
