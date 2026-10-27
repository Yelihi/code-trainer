from typing import Annotated, Literal
from pydantic import Field, StringConstraints, StrictBool
from .schema import Model

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=80)]


class Insight(Model):
    title: str = Field(min_length=1, max_length=160)
    connection_kind: Literal['known_relation', 'hypothesis']
    why: Text
    concept_ids: list[Identifier] = Field(min_length=2, max_length=4)
    assertion_ids: list[Identifier] = Field(min_length=1, max_length=3)
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=6)
    question: Text
    reading_guide: Text
    practice_guide: Text
    expected_output: Text


class InsightBundle(Model):
    suggestions: list[Insight] = Field(min_length=1, max_length=3)


class InsightRequest(Model):
    request_id: str = Field(min_length=8, max_length=80)


class InsightChoice(Model):
    index: int = Field(ge=0,le=2)
    action: Literal['adopt','skip']


class ExplorationNotes(Model):
    revision: int = Field(ge=0)
    notes: str = Field(max_length=50000)


class InsightScheduleInput(Model):
    enabled: StrictBool
    revision: int = Field(ge=0)
