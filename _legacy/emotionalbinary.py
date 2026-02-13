# emotionalbinary.py

class EmotionalBinary:
    def __init__(self, thresholds):
        self.thresholds = thresholds

    def encode(self, scores):
        return "".join(
            "1" if scores.get(cat, 0) > self.thresholds.get(cat, 0) else "0"
            for cat in ("time", "meaning", "reflection", "gravity")
        )

    def decode(self, bits):
        mp = {
            "1001": "Loyal Offering",
            "0101": "Spark",
            "0110": "Echo",
            "0011": "Seed Sent",
            "1111": "Superstate (G₀)",
            "0010": "Fragile Mirror",
            "1010": "One-Way Path",
            "0111": "Weightless Push",
            "0001": "Ghost",
        }
        return mp.get(bits, "Unknown")
