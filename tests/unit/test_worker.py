import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from media_bot.infrastructure.worker import _drain_progress, _drain_stderr, run_worker


class ServiceStub:
    def __init__(self, jobs: list[object | None], cancel: bool = False) -> None:
        self.jobs = jobs
        self.cancel = cancel
        self.failed: list[tuple[str, str]] = []
        self.completed: list[tuple[str, str, str]] = []
        self.progress: list[tuple[str, str, str, float | None]] = []

    async def claim(self) -> object | None:
        return self.jobs.pop(0)

    async def recover_expired_leases(self) -> int:
        return 0

    async def heartbeat(self, _: str, __: str) -> bool:
        return True

    async def cancellation_requested(self, _: str, __: str) -> bool:
        return self.cancel

    async def mark_cancelled(self, _: str, __: str) -> bool:
        return True

    async def fail(self, job_id: str, _: str | None, message: str) -> None:
        self.failed.append((job_id, message))

    async def complete(self, job_id: str, lease_token: str, result_path: str) -> None:
        self.completed.append((job_id, lease_token, result_path))

    async def update_progress(
        self, job_id: str, lease_token: str, stage: str, fraction: float | None
    ) -> bool:
        self.progress.append((job_id, lease_token, stage, fraction))
        return True

    async def is_cancel_requested(self, _: str) -> bool:
        return False


class PipeStub:
    def __init__(self, lines: list[bytes] | None = None) -> None:
        self.lines = lines or []

    async def readline(self) -> bytes:
        return self.lines.pop(0) if self.lines else b""


class ProcessStub:
    def __init__(self, timeout: bool = False, code: int = 0) -> None:
        self.timeout = timeout
        self.code = code
        self.killed = False
        self.pid = 123
        self.returncode: int | None = None
        self.stdout = PipeStub()
        self.stderr = PipeStub()

    async def wait(self) -> int:
        if self.timeout and not self.killed:
            await asyncio.sleep(10)
        return self.code

    def kill(self) -> None:
        self.killed = True


def job(job_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=job_id,
        lease_token="token",
        plugin_id="text_card",
        plugin_version="1",
        input_json='{"text":"test"}',
        options_json="{}",
    )


async def test_worker_marks_nonzero_runner_exit_as_failed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    service = ServiceStub([job("job-1"), None])
    process = ProcessStub(code=2)

    async def create(*_: object, **__: object) -> ProcessStub:
        return process

    async def stop(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.create_subprocess_exec", create)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        await run_worker(service, tmp_path, {"text_card"})  # type: ignore[arg-type]
    assert service.failed == [("job-1", "Runner exited with code 2")]


async def test_worker_kills_timed_out_runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    service = ServiceStub([job("job-2"), None])
    process = ProcessStub(timeout=True)

    async def create(*_: object, **__: object) -> ProcessStub:
        return process

    async def immediate_timeout(awaitable: object, **__: object) -> int:
        awaitable.close()  # type: ignore[union-attr]
        raise TimeoutError

    async def stop(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.create_subprocess_exec", create)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.wait_for", immediate_timeout)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.sleep", stop)
    signals: list[int] = []
    monkeypatch.setattr(
        "media_bot.infrastructure.worker.os.killpg", lambda _, sig: signals.append(sig)
    )
    with pytest.raises(asyncio.CancelledError):
        await run_worker(service, tmp_path, {"text_card"})  # type: ignore[arg-type]
    assert signals


async def test_worker_terminates_process_group_after_cancel_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = ServiceStub([job("job-3"), None], cancel=True)
    process = ProcessStub(timeout=True)
    process.returncode = 0
    signals: list[int] = []
    sleep_calls = 0

    async def create(*_: object, **__: object) -> ProcessStub:
        return process

    async def timeout_once(awaitable: object, **__: object) -> int:
        awaitable.close()  # type: ignore[union-attr]
        raise TimeoutError

    async def sleep(_: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 1:
            raise asyncio.CancelledError

    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.create_subprocess_exec", create)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.wait_for", timeout_once)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.sleep", sleep)
    monkeypatch.setattr(
        "media_bot.infrastructure.worker.os.killpg", lambda _, sig: signals.append(sig)
    )
    with pytest.raises(asyncio.CancelledError):
        await run_worker(service, tmp_path, {"text_card"})  # type: ignore[arg-type]
    assert signals


async def test_worker_finalizes_valid_runner_manifest_in_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    service = ServiceStub([job("job-4"), None])
    process = ProcessStub()
    command: tuple[object, ...] = ()

    async def create(*args: object, **_: object) -> ProcessStub:
        nonlocal command
        command = args
        output = Path(str(args[7]))
        output.parent.joinpath("result.png").write_bytes(b"\x89PNG\r\n\x1a\nvalid")
        output.write_text('{"path":"result.png","media_type":"image/png"}', encoding="utf-8")
        return process

    async def stop(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.create_subprocess_exec", create)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        await run_worker(service, tmp_path, {"text_card"})  # type: ignore[arg-type]

    input_path = tmp_path / "results" / "job-4" / "input.json"
    assert command[3] == "run-payload"
    assert '"plugin_id":"text_card"' in input_path.read_text(encoding="utf-8")
    assert service.completed == [("job-4", "token", str(input_path.parent / "result.png"))]
    assert service.failed == []


async def test_worker_rejects_invalid_runner_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    service = ServiceStub([job("job-5"), None])

    async def create(*args: object, **_: object) -> ProcessStub:
        output = Path(str(args[7]))
        output.write_text('{"path":"../outside.png","media_type":"image/png"}', encoding="utf-8")
        return ProcessStub()

    async def stop(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.create_subprocess_exec", create)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        await run_worker(service, tmp_path, {"text_card"})  # type: ignore[arg-type]

    assert service.completed == []
    assert service.failed and service.failed[0][0] == "job-5"


async def test_worker_persists_valid_runner_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    service = ServiceStub([job("job-6"), None])
    process = ProcessStub()
    process.stdout = PipeStub([b'{"type":"progress","stage":"rendering","fraction":0.5}\n'])

    async def create(*args: object, **_: object) -> ProcessStub:
        output = Path(str(args[7]))
        output.parent.joinpath("result.png").write_bytes(b"\x89PNG\r\n\x1a\nvalid")
        output.write_text('{"path":"result.png","media_type":"image/png"}', encoding="utf-8")
        return process

    async def stop(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.create_subprocess_exec", create)
    monkeypatch.setattr("media_bot.infrastructure.worker.asyncio.sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        await run_worker(service, tmp_path, {"text_card"})  # type: ignore[arg-type]

    assert service.progress == [("job-6", "token", "rendering", 0.5)]


async def test_progress_and_stderr_drainers_ignore_invalid_runner_output() -> None:
    service = ServiceStub([])
    await _drain_progress(None, service, "job", "token")  # type: ignore[arg-type]
    await _drain_progress(
        PipeStub(
            [
                b"not json\n",
                b'{"type":"ignored","stage":"skip"}\n',
                b'{"type":"progress","stage":"rendering","fraction":0.25}\n',
                b"x" * 4097,
            ]
        ),
        service,  # type: ignore[arg-type]
        "job",
        "token",
    )
    await _drain_stderr(None, "job")
    await _drain_stderr(PipeStub([b"renderer message\n", b"x" * 4097]), "job")
    assert service.progress == [("job", "token", "rendering", 0.25)]
