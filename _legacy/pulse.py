import threading
import time
from datetime import datetime

class Pulse(threading.Thread):
    def __init__(self, system, interval=300):
        super().__init__(daemon=True)
        self.system = system
        self.interval = max(5, int(interval))
        self._stop = threading.Event()
        self._paused = threading.Event()

    def run(self):
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.2)
                continue

            time.sleep(self.interval)
            if self._stop.is_set():
                break

            self.run_once()

    def run_once(self):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n[PACK PULSE {ts}] Autonomous reflection...")

        try:
            s = self.system.synthesizer.synthesize()
            if s:
                print(f"[PACK SYNTHESIS] {s}")
                if self.system.reflection_logger:
                    self.system.reflection_logger.log(
                        emotion="auto",
                        synthesis=s,
                        keywords=[],
                        source="pulse",
                    )
        except Exception as e:
            print("[PULSE ERROR]:", e)

        print("=" * 40)

    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    def stop(self):
        self._stop.set()
        self._paused.clear()
