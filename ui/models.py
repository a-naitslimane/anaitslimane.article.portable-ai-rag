from typing import Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    category: str = "auto"
    mode: str = "hybrid"
    top_k: Optional[int] = None

class ApplicationException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code