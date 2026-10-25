from typing import Literal
from pydantic import Field
from .schema import Model

MaterialKind = Literal['interpretation', 'practice']


class MaterialReviewInput(Model):
    revision: int = Field(ge=1)
