from pydantic import Field, model_validator
from .schema import Model, Text


class InterpretationInput(Model):
    request_id: str = Field(min_length=8, max_length=80)
    resource_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(ge=1)


class InterpretationSection(Model):
    id: str = Field(pattern=r'^s[1-6]$')
    title: str = Field(min_length=1, max_length=160)
    body: Text
    prerequisites: list[str] = Field(max_length=5)
    source_quotes: list[str] = Field(min_length=1, max_length=3)
    examples: list[Text] = Field(max_length=3)
    extensions: list[Text] = Field(max_length=3)
    questions: list[Text] = Field(min_length=1, max_length=4)


class InterpretationDraft(Model):
    title: str = Field(min_length=1, max_length=160)
    summary: Text
    concepts: list[Text] = Field(min_length=1, max_length=12)
    sections: list[InterpretationSection] = Field(min_length=1, max_length=6)

    @model_validator(mode='after')
    def ordered(self):
        seen = set()
        for section in self.sections:
            if section.id in seen or not set(section.prerequisites) <= seen:
                raise ValueError('Section prerequisites must refer to earlier sections')
            if any(not quote.strip() or len(quote) > 1200 for quote in section.source_quotes):
                raise ValueError('Source quotes must be nonempty and at most 1200 characters')
            seen.add(section.id)
        return self
