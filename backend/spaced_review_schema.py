from typing import Literal
from pydantic import Field
from .schema import Model

ReviewKind = Literal['interpretation', 'practice', 'note']


class ReviewEnrollment(Model):
    kind: ReviewKind
    origin_id: str = Field(min_length=1, max_length=80)
    revision: int = Field(ge=1)


class ReviewResponse(Model):
    request_id: str = Field(min_length=8, max_length=80)
    revision: int = Field(ge=0)
    response: Literal['can_explain', 'needs_review']
