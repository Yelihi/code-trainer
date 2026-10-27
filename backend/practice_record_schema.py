from typing import Annotated
from pydantic import Field
from .schema import Model


class PracticeRecordInput(Model):
    request_id: str = Field(min_length=8, max_length=80)
    revision: int = Field(ge=0)
    answers: dict[Annotated[str, Field(pattern=r'^q(?:[1-9]|1[0-2])$')], Annotated[str, Field(max_length=20000)]] = Field(max_length=12)
    summary: str = Field(max_length=50000)
