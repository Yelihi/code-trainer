from pydantic import Field
from .schema import Model


class AISettingsRevision(Model):
    revision: int = Field(ge=0)


class AISettingsInput(AISettingsRevision):
    api_key: str = Field(min_length=1, max_length=1000, pattern=r'^[\x21-\x7e]+$', repr=False)
    model: str = Field(min_length=1, max_length=200, pattern=r'^[A-Za-z0-9_./:-]+$')
    provider_url: str = Field(min_length=1, max_length=500)
