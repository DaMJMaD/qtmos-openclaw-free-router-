import sys
from pathlib import Path

# --- Ensure local imports work ---
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Core system imports ---
from CognitiveSystem import CognitiveSystem
from printhelp import print_help

# --- Collective cognition imports (SAFE even if unused yet) ---
from collective_review import merge_points, reinforce_points
from collective_points import Point

# -------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------

def main():
    print("[MAIN]: Booting Cognitive System...")
    system = CognitiveSystem()
    print_help()
    print("[MAIN]: System online.")

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue

            if line in ("exit", "quit"):
                print("[MAIN]: Shutdown.")
                break

            system.handle_command(line)

        except KeyboardInterrupt:
            print("\n[MAIN]: Interrupted.")
            break
        except Exception as e:
            print("[MAIN ERROR]:", e)


# -------------------------------------------------
# EXPERIMENTAL COLLECTIVE LOGIC (DISABLED FOR NOW)
# -------------------------------------------------
# This stays commented until prompts + adapters exist

"""
# Example scaffold — DO NOT RUN YET

from llm_adapters import llm_adapters

prompts = [
    "Example prompt 1",
    "Example prompt 2"
]

gpt_points = []

for prompt_id, prompt in enumerate(prompts):
    response = llm_adapters.call("gpt", prompt)
    gpt_points.append(
        Point(
            model="gpt",
            prompt_id=prompt_id,
            content=response
        )
    )

all_points = merge_points(gpt_points)
reinforced = reinforce_points(all_points)
"""

# -------------------------------------------------

if __name__ == "__main__":
    main()
