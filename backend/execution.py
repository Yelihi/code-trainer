"""The only contract exposed by the isolated runner; never accepts Docker options."""
from typing import Annotated
from pydantic import Field
from .schema import Language, Model

RuntimeId = Annotated[str, Field(pattern=r'^sha256:[0-9a-f]{64}$')]


class ExecutionRequest(Model):
    language: Language
    code: str = Field(max_length=64000)
    inputs: list[Annotated[str, Field(max_length=6000)]] = Field(min_length=1, max_length=8)
    image_id: RuntimeId | None = None


class Runtime(Model):
    image_id: RuntimeId


class Result(Model):
    status: Annotated[str, Field(pattern=r'^(ok|error|runtime_error|time_limit|output_limit|memory_limit|compile_error|compile_time_limit|compile_output_limit|compile_memory_limit)$')]
    stdout: str = Field(max_length=16384)
    stderr: str = Field(max_length=16384)
    exit_code: int | None


class ExecutionResponse(Model):
    results: list[Result] = Field(min_length=1, max_length=8)
