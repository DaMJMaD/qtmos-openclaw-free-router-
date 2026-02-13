# synthesis.py

import re
from collections import Counter


class Synthesizer:
    def __init__(self, learning_system, formula, encoder):
        self.learning_system = learning_system
        self.formula = formula
        self.encoder = encoder

    def find_dominant_emotion(self):
        with self.learning_system._lock:
            all_mem = (
                self.learning_system.core_learning_history +
                self.learning_system.episodic_learning_history
            )

        if not all_mem:
            return None, []

        names = [
            m.get("emotional_state", {}).get("name", "Unknown")
            for m in all_mem
        ]

        dom = Counter(names).most_common(1)[0][0]

        mems = [
            m.get("input", "")
            for m in all_mem
            if m.get("emotional_state", {}).get("name") == dom
        ]

        return dom, mems

    def extract_keywords(self, texts):
        words = Counter()
        for t in texts:
            for w in re.findall(r"\b\w+\b", (t or "").lower()):
                if len(w) > 3:
                    words[w] += 1
        return words.most_common(5)

    def synthesize(self):
        dom, mems = self.find_dominant_emotion()
        if not mems:
            return None

        kws = [k for k, _ in self.extract_keywords(mems)]
        focus = ", ".join(kws[:4]) if kws else "alignment"

        return f"SYNTHESIS: Patterns around {focus} dominate recent cognition."
