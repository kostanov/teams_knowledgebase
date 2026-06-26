from pydantic import BaseModel, Field, model_validator


class SourceItem(BaseModel):
    document_id: str
    quote: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2_000)


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    needs_review: bool

    @model_validator(mode="after")
    def validate_sources_consistency(self) -> "AskResponse":
        if not self.sources and not self.needs_review:
            raise ValueError("sources must not be empty when needs_review=false")
        if self.sources and self.needs_review is False:
            return self
        if not self.sources:
            self.needs_review = True
        return self
