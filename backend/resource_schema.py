"""Raw registration is independent of AI generation and sandbox settings."""
from typing import Literal
from pydantic import Field, model_validator
from .schema import Model
from .note_schema import Label


class ResourceInput(Model):
    request_id: str = Field(min_length=8, max_length=80)
    resource_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(default=0, ge=0)
    kind: Literal['text', 'url']
    name: Label
    url: str = Field(default='', max_length=2000)
    content: str = Field(default='', max_length=60000)
    feed_post_id: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode='after')
    def source_fields(self):
        self.url = self.url.strip()
        if self.feed_post_id and self.kind != 'url':
            raise ValueError('RSA 글은 URL로 등록해주세요.')
        if self.kind == 'text' and (not self.content.strip() or self.url):
            raise ValueError('텍스트 본문을 입력해주세요. URL은 URL 등록에서 사용해주세요.')
        if self.kind == 'url' and (not self.url or self.content):
            raise ValueError('URL 등록에는 주소만 입력해주세요.')
        return self
