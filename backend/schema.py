from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Language = Literal['javascript', 'typescript', 'python', 'cpp', 'rust']
Difficulty = Literal['beginner', 'intermediate', 'advanced']
Text = Annotated[str, Field(min_length=1, max_length=6000)]
Code = Annotated[str, Field(max_length=24000)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class LearningOutcome(Model):
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]
    exercise_ids: list[str] = Field(min_length=1, max_length=200)


class LearnedConcept(Model):
    root_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    outcomes: list[LearningOutcome] = Field(min_length=1, max_length=50)


class LearningSummary(Model):
    concepts: list[LearnedConcept] = Field(min_length=1, max_length=100)


class Credentials(Model):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: str = Field(min_length=8, max_length=128)
    admin_password: str = Field(default='', max_length=128)


class GenerationInput(Model):
    request_id: str = Field(min_length=8, max_length=80)
    source_kind: Literal['text', 'url', 'context', 'sample']
    source: str = Field(default='', max_length=60000)
    context_id: str | None = None
    unit_id: str | None = Field(default=None, min_length=1, max_length=80)
    feed_post_id: str | None = Field(default=None, min_length=1, max_length=80)
    language: Language = 'javascript'
    difficulty: Difficulty = 'beginner'
    source_name: str = Field(default='', max_length=255)
    framework: str = Field(default='', max_length=80)

    @model_validator(mode='after')
    def source_valid(self):
        if self.feed_post_id and self.source_kind != 'url':
            raise ValueError('대기 포스팅은 URL 자료로 등록해주세요.')
        if self.unit_id and self.source_kind != 'context':
            raise ValueError('단원 문제는 저장된 학습 과정에서 생성해주세요.')
        if self.source_kind == 'context':
            if not self.context_id or self.source:
                raise ValueError('Context 입력을 확인해주세요.')
        elif self.context_id:
            raise ValueError('자료와 Context를 함께 입력할 수 없습니다.')
        if self.source_kind in ('text', 'url') and not self.source.strip():
            raise ValueError('자료를 입력해주세요.')
        if self.source_kind == 'sample' and (self.source or self.language != 'javascript'):
            raise ValueError('예제는 JavaScript를 사용합니다.')
        return self


class Requirement(Model):
    id: str = Field(pattern=r'^r[1-9]$')
    text: Text


class Case(Model):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,30}$')
    code: str = Field(default='', max_length=6000)
    stdin: str = Field(max_length=2000)
    expected: str = Field(max_length=4000)
    requirements: list[str] = Field(min_length=1, max_length=4)


class WrongSolution(Model):
    code: Code
    requirement: str
    failing_test: str
    reason: Text


class Evaluation(Model):
    reference: Code
    alternative: Code = ''  # Optional legacy review material, not required for new exercises.
    hidden_tests: list[Case] = Field(max_length=4)
    wrong_solutions: list[WrongSolution] = Field(default_factory=list, max_length=4)
    read_answer: str = Field(max_length=4000)


class FixStarterRepair(Model):
    starter: Code
    hints: list[Text] = Field(min_length=1, max_length=3)


class ExerciseCodeRepair(Model):
    starter: Code
    reference: Code
    public_tests: list[Case] = Field(min_length=1, max_length=4)
    hidden_tests: list[Case] = Field(min_length=1, max_length=4)


class ExerciseDraft(Model):
    kind: Literal['READ', 'FIX', 'MODIFY', 'BUILD']
    test_mode: Literal['stdio', 'code'] = 'stdio'
    title: str = Field(min_length=1, max_length=160)
    description: Text
    requirements: list[Requirement] = Field(min_length=1, max_length=4)
    starter: Code
    public_tests: list[Case] = Field(min_length=1, max_length=4)
    hints: list[Text] = Field(min_length=1, max_length=3)
    evaluation: Evaluation

    @model_validator(mode='after')
    def coverage(self):
        reqs = {r.id for r in self.requirements}
        tests = self.public_tests + self.evaluation.hidden_tests
        if self.test_mode == 'code':
            if self.kind == 'READ' or any(not t.code.strip() or t.stdin for t in tests):
                raise ValueError('Code tests require call snippets and no stdin')
        elif any(t.code for t in tests):
            raise ValueError('Stdio tests cannot include code')
        ids = {t.id for t in tests}
        if len(reqs) != len(self.requirements) or len(ids) != len(tests):
            raise ValueError('Duplicate requirement or test ID')
        if any(not set(t.requirements) <= reqs for t in tests):
            raise ValueError('Unknown test requirement')
        if set().union(*(set(t.requirements) for t in tests)) != reqs:
            raise ValueError('Missing test coverage')
        if self.kind == 'READ':
            if (not self.starter.strip() or not self.evaluation.read_answer.strip() or self.evaluation.reference != self.starter
                    or self.evaluation.hidden_tests or self.evaluation.wrong_solutions
                    or any(t.stdin or t.expected for t in self.public_tests)):
                raise ValueError('READ needs a nonempty prediction and a no-input program without public answers')
        if self.kind != 'READ':
            if not self.evaluation.hidden_tests or not self.evaluation.reference.strip():
                raise ValueError('Hidden tests and a reference solution required')
            for wrong in self.evaluation.wrong_solutions:
                if not any(t.id == wrong.failing_test and wrong.requirement in t.requirements for t in tests):
                    raise ValueError('Wrong solution must name a relevant test')
        return self


class LessonSection(Model):
    title: str = Field(min_length=1, max_length=160)
    body: Text
    code: Code = ''
    output: str = Field(default='', max_length=4000)
    walkthrough: str = Field(max_length=6000, description='Step-by-step explanation of the example; nonempty when code is provided.')


class Checkpoint(Model):
    question: Text
    answer: Text


class SourceExample(Model):
    id: str
    section: str
    language: str
    code: Code


class LearningUnit(Model):
    id: str = Field(pattern=r'^u[1-6]$')
    title: str = Field(min_length=1, max_length=160)
    objective: Text
    concepts: list[Text] = Field(min_length=1, max_length=8)
    prerequisites: list[str] = Field(max_length=5)
    rationale: Text
    lesson: list[LessonSection] = Field(min_length=2, max_length=5)
    pitfalls: list[Text] = Field(min_length=1, max_length=4)
    checkpoints: list[Checkpoint] = Field(min_length=1, max_length=4)
    source_example_ids: list[str] = Field(default_factory=list, max_length=4)
    source_examples: list[SourceExample] = Field(default_factory=list, max_length=4)

    @model_validator(mode='after')
    def has_example(self):
        if not any(s.code.strip() and s.walkthrough.strip() for s in self.lesson):
            raise ValueError('A lesson needs a code example and a walkthrough')
        return self


class ContextDraft(Model):
    title: str = Field(min_length=1, max_length=160)
    description: Text
    summary: Text
    concepts: list[Text] = Field(min_length=1, max_length=8)
    learning_notes: str = Field(min_length=1, max_length=6000)
    language: Language
    difficulty: Difficulty = 'beginner'
    framework: str = Field(default='', max_length=80)
    units: list[LearningUnit] = Field(default_factory=list, max_length=6)

    @model_validator(mode='after')
    def curriculum_order(self):
        seen = set()
        for unit in self.units:
            if unit.id in seen or not set(unit.prerequisites) <= seen:
                raise ValueError('Unit prerequisites must refer to earlier units')
            seen.add(unit.id)
        # Concept names describe scope, not identifiers: units may revisit or refine them.
        return self


class CurriculumDraft(ContextDraft):
    units: list[LearningUnit] = Field(min_length=1, max_length=6)


class SetDraft(Model):
    title: str = Field(min_length=1, max_length=160)
    concept: Text
    exercises: list[ExerciseDraft] = Field(min_length=4, max_length=4)

    @model_validator(mode='after')
    def ordered(self):
        if [e.kind for e in self.exercises] != ['READ', 'FIX', 'MODIFY', 'BUILD']:
            raise ValueError('Expected READ, FIX, MODIFY, BUILD in that order')
        return self


class DraftInput(Model):
    code: Code = ''
    answer: str = Field(default='', max_length=4000)
    revision: int = Field(ge=0)


class ExecutionInput(Model):
    review_id: str | None = Field(default=None, min_length=1, max_length=80)
    request_id: str = Field(min_length=8, max_length=80)
    version: int = Field(ge=1)
    action: Literal['run', 'test', 'submit']
    code: Code = ''
    answer: str = Field(default='', max_length=4000)
    stdin: str = Field(default='', max_length=2000)
    test_code: str = Field(default='', max_length=6000)


class ReportInput(Model):
    message: str = Field(min_length=5, max_length=2000)
    attempt_id: str | None = None


class ReportUpdate(Model):
    status: Literal['reviewed', 'resolved']
    withdraw: bool = False
