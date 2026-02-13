# collective_review.py

from typing import List
from collective_points import Point

def merge_points(*point_lists: List[Point]) -> List[Point]:
    merged = []
    for plist in point_lists:
        merged.extend(plist)
    return merged


def reinforce_points(points: List[Point]) -> List[Point]:
    # Placeholder reinforcement
    for p in points:
        p.weight += 0.0
    return points
