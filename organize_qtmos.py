"""
QTMoS Folder Organizer
---------------------
• Scans current directory
• Moves files into intention-based folders
• Never deletes anything
• Creates a _legacy mirror for safety
• Writes a REPORT.md with all actions
"""

from pathlib import Path
import shutil
import datetime

BASE = Path(__file__).resolve().parent
LEGACY = BASE / "_legacy"
REPORT = BASE / "REPORT.md"

# ---------- classification rules ----------

RULES = {
    "core": [
        "main.py",
        "CognitiveSystem.py",
        "commandbridge.py",
    ],
    "llm": [
        "llm_adapters.py",
        "mcp",
        "gemini",
    ],
    "memory": [
        "memory",
        "persona",
        "MetaDB",
        "recursive",
    ],
    "cognition": [
        "cognition",
        "emotion",
        "tone",
        "synthesis",
    ],
    "runtime": [
        "pulse",
        "runtime",
    ],
    "collective": [
        "collective",
    ],
    "utils": [
        "printhelp",
        "logger",
    ],
}

# ---------- helpers ----------

def classify(path: Path) -> str | None:
    name = path.name.lower()
    for folder, keys in RULES.items():
        if any(k.lower() in name for k in keys):
            return folder
    return None

def safe_move(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return f"SKIPPED (exists): {dst}"
    shutil.move(str(src), str(dst))
    return f"MOVED: {src.name} → {dst.parent.name}/"

# ---------- main ----------

def main():
    lines = []
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    lines.append(f"# QTMoS Organization Report\n\nRun: {timestamp}\n")

    LEGACY.mkdir(exist_ok=True)

    for item in BASE.iterdir():
        if item.name.startswith("_") or item.name in (
            "organize_qtmos.py",
            "REPORT.md",
        ):
            continue

        if item.is_dir() and item.name == "MetaDB":
            target = BASE / "memory" / "MetaDB"
        else:
            folder = classify(item)
            if not folder:
                continue
            target = BASE / folder / item.name

        # backup
        backup = LEGACY / item.name
        if not backup.exists():
            if item.is_dir():
                shutil.copytree(item, backup)
            else:
                shutil.copy2(item, backup)

        result = safe_move(item, target)
        lines.append(result)

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("[ORGANIZER]: Done. See REPORT.md and _legacy/")

if __name__ == "__main__":
    main()
