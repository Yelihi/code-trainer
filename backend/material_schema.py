from typing import Literal
from pydantic import Field
from .schema import Model

MaterialKind = Literal['interpretation', 'practice']


class MaterialReviewInput(Model):
    revision: int = Field(ge=1)


class MaterialProposalInput(Model):
    request_id: str = Field(min_length=8, max_length=80)
