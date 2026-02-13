import json
import time
from llm.llm_adapters import ask_router

COMMAND_FILE = r"C:\mindustry\command.json"

def send_action(action: dict):
    with open(COMMAND_FILE, "w") as f:
        json.dump(action, f)

def ai_step(prompt):
    response, engine = ask_router(prompt)
    print(f"[AI:{engine}] {response}")
    return response

def build_conveyor_line():
    send_action({"type": "key", "key": "b"})
    time.sleep(0.2)
    send_action({
        "type": "drag",
        "x1": 420, "y1": 300,
        "x2": 520, "y2": 300
    })

if __name__ == "__main__":
    print("AI Mindustry Router online.")
    while True:
        cmd = input(">> ")
        if cmd == "build":
            build_conveyor_line()
        else:
            ai_step(cmd)
