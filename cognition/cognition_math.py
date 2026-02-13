# cognition_math.py
class V0Formula:
    def __init__(self, weights):
        self.weights = weights

    def calculate(self, text: str) -> dict:
        scores = {k: 0 for k in self.weights}
        words = text.lower().split()
        for cat, table in self.weights.items():
            for w in words:
                if w in table:
                    scores[cat] += table[w]
        return scores
