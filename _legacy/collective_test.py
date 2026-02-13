# collective_test.py
# Safe sandbox to test collective cognition logic

from collective_points import Point
from collective_review import merge_points, reinforce_points


def run_test():
    print("[TEST]: Starting collective cognition test")

    # -----------------------------
    # Fake prompts (shared context)
    # -----------------------------
    prompts = [
        "The system should favor consensus over novelty",
        "Independent analysis reduces hallucinations",
        "Shared review strengthens weak signals",
        "Single standout ideas should not dominate",
        "Agreement increases confidence, not authority",
    ]

    # --------------------------------
    # Simulated model outputs
    # (pretend these came from models)
    # --------------------------------

    gpt_points = [
        Point("gpt", 0, "Consensus across models improves reliability"),
        Point("gpt", 1, "Independent reasoning reduces hallucinations"),
        Point("gpt", 2, "Shared review builds stronger understanding"),
        Point("gpt", 3, "Single ideas should not dominate outcomes"),
        Point("gpt", 4, "Agreement builds confidence"),
    ]

    grok_points = [
        Point("grok", 0, "Consensus improves reliability"),
        Point("grok", 1, "Independent analysis reduces hallucinations"),
        Point("grok", 2, "Collective review strengthens insights"),
        Point("grok", 3, "Outliers should not control decisions"),
        Point("grok", 4, "Agreement does not imply authority"),
    ]

    # -----------------------------
    # Merge phase (shared exposure)
    # -----------------------------
    all_points = merge_points(gpt_points, grok_points)

    print(f"[TEST]: Merged {len(all_points)} points")

    # -----------------------------
    # Reinforcement phase
    # -----------------------------
    reinforced = reinforce_points(all_points)

    # -----------------------------
    # Display results
    # -----------------------------
    print("\n[TEST]: Reinforced Points (sorted by weight)\n")

    reinforced_sorted = sorted(
        reinforced,
        key=lambda p: p.weight,
        reverse=True
    )

    for p in reinforced_sorted:
        print(f"[{p.model.upper()} | weight={p.weight:.2f}] {p.content}")


if __name__ == "__main__":
    run_test()
