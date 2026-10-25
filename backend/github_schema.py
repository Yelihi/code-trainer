from typing import Annotated, Literal
from pydantic import Field, StringConstraints
from .schema import Model


class GitHubConnection(Model):
    token: str = Field(pattern=r'^github_pat_[A-Za-z0-9_]{20,240}$', repr=False)


class GitHubRepository(Model):
    url: str = Field(min_length=1, max_length=500)


class GitHubDefaultRepository(GitHubRepository):
    connection_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    repo_id: int = Field(gt=0)
    private: bool


class GitHubSource(Model):
    kind: Literal['note', 'concept', 'learning']
    id: str = Field(min_length=1, max_length=150)


class GitHubPublish(GitHubSource, GitHubRepository):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    connection_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    repo_id: int = Field(gt=0)
    private: bool
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60000)]
    permissions_confirmed: Literal[True]
    content_confirmed: Literal[True]


class GitHubRecovery(Model):
    url: str = Field(min_length=1, max_length=500)
