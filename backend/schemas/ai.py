from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AISourceQuote(BaseModel):
    quote: str = Field(..., min_length=1)


class AIAnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2_000)
    context: str = Field(..., min_length=1, max_length=50_000)


class AIAnswerResponse(BaseModel):
    answer: str
    sources: list[AISourceQuote]
    confidence: Literal["high", "medium", "low"]
    needs_review: bool

    @model_validator(mode="after")
    def enforce_review_rules(self) -> "AIAnswerResponse":
        if self.confidence == "low":
            object.__setattr__(self, "needs_review", True)
        if not self.sources:
            object.__setattr__(self, "needs_review", True)
        return self
