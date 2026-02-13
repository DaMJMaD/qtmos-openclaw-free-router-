# memory_models.py
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

@dataclass
class CortexPack:
    name: str
    data: Dict[str, Any]
    path: Path

@dataclass
class EpisodicPack:
    name: str
    data: Dict[str, Any]
    path: Path
    timestamp: Optional[float] = None
    tags: List[str] = None

@dataclass
class ProfilePack:
    name: str
    data: Dict[str, Any]
    path: Path
