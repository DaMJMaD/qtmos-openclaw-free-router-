from dataclasses import dataclass
from datetime import datetime

@dataclass
class Point:
    model: str
    prompt_id: int
    content: str
    weight: float = 1.0
    timestamp: datetime = datetime.utcnow()
