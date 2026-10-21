from typing import Annotated, Literal
from pydantic import Field, StringConstraints
from .schema import Model

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]
Relation = Literal['CLAIM', 'PREREQUISITE_OF', 'BROADER_THAN', 'USED_IN', 'RELATED_TO']


class ReferenceMetadata(Model):
    kind: Literal['book', 'lecture', 'article', 'experience', 'other'] = 'other'
    title: str = Field(default='', max_length=300)
    author: str = Field(default='', max_length=200)
    url: str = Field(default='', max_length=2000)
    locator: str = Field(default='', max_length=300)


class ReferenceInput(Model):
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(ge=0)
    title: Label
    body: str = Field(min_length=1, max_length=60000)
    metadata: ReferenceMetadata


class ImageInput(Model):
    name: str = Field(max_length=200)
    content: str = Field(min_length=1, max_length=5600000)


class ConceptCandidate(Model):
    key: Label
    existing_id: str = Field(max_length=100)
    pref_label: Label
    definition: Description
    scope: str = Field(max_length=200)
    aliases: list[Label] = Field(max_length=12)
    quote: Description
    basis: Literal['source', 'interpretation', 'question']


class AssertionCandidate(Model):
    subject: Label
    kind: Relation
    object: str = Field(max_length=160)
    text: Description
    scope: str = Field(max_length=200)
    quote: Description
    basis: Literal['source', 'interpretation', 'question']
    disposition: Literal['supports', 'refutes'] = 'supports'


class KnowledgeProposal(Model):
    concepts: list[ConceptCandidate] = Field(min_length=1, max_length=16)
    assertions: list[AssertionCandidate] = Field(max_length=24)


class NoteIssue(Model):
    kind: Literal['correction_needed', 'needs_verification']
    quote: Description
    explanation: Description
    suggestion: Description


class NoteContentReview(Model):
    summary: Description
    issues: list[NoteIssue] = Field(max_length=12)


class ReviewedKnowledgeProposal(KnowledgeProposal):
    review: NoteContentReview


class RevisionInput(Model):
    revision: int = Field(ge=1)


class ArchiveInput(Model):
    archived: bool


class RegisterKnowledge(RevisionInput):
    request_id: str = Field(min_length=8, max_length=80)
    proposal_id: str | None = Field(default=None, max_length=100)
    data: KnowledgeProposal


class ReviewStart(Model):
    request_id: str = Field(min_length=8, max_length=80)
    note_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class ReviewAnswer(Model):
    request_id: str = Field(min_length=8, max_length=80)
    revision: int = Field(ge=0)
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


class ReferenceReviewFeedback(Model):
    feedback: Description
    question: Description
    citations: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(min_length=1, max_length=6)
