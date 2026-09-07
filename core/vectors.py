import numpy as np
 
 
def normalize(vector: list[float]) -> list[float]:
    v = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(v)
    if norm == 0:
        return vector
    return (v / norm).tolist()
