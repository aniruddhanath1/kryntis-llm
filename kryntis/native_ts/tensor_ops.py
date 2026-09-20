"""Pure Python tensor utility operations."""

import math
from typing import List

class TensorOperations:
    """Mathematical vector operations without heavy dependencies."""
    @staticmethod
    def dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return TensorOperations.dot(a, b) / (norm_a * norm_b)
