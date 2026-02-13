from pathlib import Path
import json
import time

from memory_models import CortexPack, EpisodicPack, ProfilePack
from typing import Dict, Any, List, Optional




class PersonalityDB:
    """
    Simple loader/index over:
      - Core pack
      - Episodic packs
      - Profile packs
    """


    def __init__(self, meta_dir=None, persona_dir=None, profile_dir=None):
        self.meta_dir = meta_dir
        self.persona_dir = persona_dir
        self.profile_dir = profile_dir



    # ---------- helpers ----------

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # ---------- core ----------

    def load_core(self) -> CortexPack:
        path = CORE_PATH
        if not path.exists():
            # create minimal core if missing
            path.write_text(
                json.dumps(
                    {"traits": {}, "created": time.time()},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        data = self._load_json(path)
        return CortexPack(name=path.stem, data=data, path=path)

    # ---------- episodic ----------

    def list_episodic(self) -> List[str]:
        if not self.persona_dir.exists():
            return []
        names = []
        for p in self.persona_dir.glob("*.json"):
            # keep your naming vibe: packX_episodic.json etc.
            if "episodic" in p.name.lower() or "pack" in p.name.lower():
                names.append(p.stem)
        return sorted(names)

    def resolve_episodic_name(self, name: str) -> Optional[Path]:
        """
        Apply aliasing similar to switch_episodic_pack:
          '0', 'base', 'empty', 'clear', 'quantum', etc.
        """
        name = (name or "").strip().strip('"').strip("'")
        if not name:
            return None

        alias_map = {
            "0": BASE_EMPTY_PACK.name,
            "base": BASE_EMPTY_PACK.name,
            "empty": BASE_EMPTY_PACK.name,
            "clear": BASE_EMPTY_PACK.name,
            "quantum": "packQuantum_episodic.json",
            "q": "packQuantum_episodic.json",
            "einstein": "packEinstein_episodic.json",
        }

        base_dir = self.persona_dir
        if name in alias_map:
            target = base_dir / alias_map[name]
            return target if target.exists() else None

        candidates = []
        if name.lower().endswith(".json"):
            candidates.append(base_dir / name)
        candidates.extend(
            [
                base_dir / f"{name}.json",
                base_dir / f"pack{name}.json",
                base_dir / f"{name}_episodic.json",
                base_dir / f"pack{name}_episodic.json",
            ]
        )
        for c in candidates:
            if c.exists():
                return c
        return None

    def load_episodic(self, name: str) -> EpisodicPack:
        path = self.resolve_episodic_name(name)
        if not path:
            raise FileNotFoundError(f"No episodic pack found for '{name}' in {self.persona_dir}")
        data = self._load_json(path)
        meta = data.get("_meta", {})
        return EpisodicPack(
            name=path.stem,
            data=data,
            path=path,
            timestamp=meta.get("timestamp"),
            tags=meta.get("tags") or [],
        )

    # ---------- profiles ----------

    def list_profiles(self) -> List[str]:
        if not self.profile_dir.exists():
            return []
        return sorted([p.stem for p in self.profile_dir.glob("*.json")])

    def load_profile(self, name: str) -> ProfilePack:
        name = (name or "").strip().strip('"').strip("'")
        if not name:
            raise ValueError("profile name required")
        base_dir = self.profile_dir
        candidates = []
        if name.lower().endswith(".json"):
            candidates.append(base_dir / name)
        candidates.append(base_dir / f"{name}.json")

        path = next((c for c in candidates if c.exists()), None)
        if not path:
            raise FileNotFoundError(f"No profile found for '{name}' in {base_dir}")
        data = self._load_json(path)
        return ProfilePack(name=path.stem, data=data, path=path)

