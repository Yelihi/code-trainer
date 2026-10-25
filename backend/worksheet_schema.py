from pydantic import Field, model_validator
from .schema import Model, Text


class WorksheetInput(Model):
    request_id: str = Field(min_length=8, max_length=80)
    interpretation_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class WorksheetQuestion(Model):
    id: str = Field(pattern=r'^q(?:[1-9]|1[0-2])$')
    section_id: str = Field(pattern=r'^s[1-6]$')
    prompt: Text


class WorksheetDraft(Model):
    title: str = Field(min_length=1, max_length=160)
    questions: list[WorksheetQuestion] = Field(min_length=1, max_length=12)

    @model_validator(mode='after')
    def distinct(self):
        if not self.title.strip() or any(not q.prompt.strip() for q in self.questions):
            raise ValueError('Worksheet text must not be blank')
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError('Question IDs must be unique')
        return self
