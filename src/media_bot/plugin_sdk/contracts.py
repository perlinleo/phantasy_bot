from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel


class ImageResult(BaseModel):
    kind: str = "image"
    path: str
    media_type: str = "image/png"


@dataclass(frozen=True)
class JobContext:
    workspace: Path
    job_id: str = ""
    attempt_id: str = ""
    _reporter: Callable[[str, float | None], None] | None = field(
        default=None, repr=False, compare=False
    )

    def report(self, stage: str, fraction: float | None = None) -> None:
        if fraction is not None and not 0 <= fraction <= 1:
            raise ValueError("Progress fraction must be between 0 and 1")
        if self._reporter is not None:
            self._reporter(stage, fraction)


@dataclass(frozen=True)
class PluginSpec[InputT: BaseModel, OptionsT: BaseModel]:
    id: str
    version: str
    title: str
    description: str
    input_model: type[InputT]
    options_model: type[OptionsT]
    run: Callable[[InputT, OptionsT, JobContext], Awaitable[ImageResult]]
    category: str = "other"
    tags: tuple[str, ...] = ()
