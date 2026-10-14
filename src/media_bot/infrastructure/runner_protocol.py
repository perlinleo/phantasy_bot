from pathlib import PurePosixPath

from pydantic import BaseModel, Field, field_validator


class RunnerInput(BaseModel):
    job_id: str
    lease_token: str
    plugin_id: str
    plugin_version: str
    input_json: str
    options_json: str
    workspace: str


class RunnerResult(BaseModel):
    path: str = Field(min_length=1)
    media_type: str

    @field_validator("path")
    @classmethod
    def relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("result path must be relative to workspace")
        return value


class ProgressEvent(BaseModel):
    type: str = "progress"
    stage: str = Field(min_length=1, max_length=128)
    fraction: float | None = Field(default=None, ge=0, le=1)
