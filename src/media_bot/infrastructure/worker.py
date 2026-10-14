import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

from media_bot.application.jobs import JobService
from media_bot.infrastructure.artifacts import validate_artifact
from media_bot.infrastructure.runner_protocol import ProgressEvent, RunnerInput, RunnerResult

LOG = logging.getLogger(__name__)


async def _drain_progress(
    reader: asyncio.StreamReader | None, service: JobService, job_id: str, lease_token: str
) -> None:
    if reader is None:
        return
    last_stage = ""
    last_fraction: float | None = None
    last_update = 0.0
    while line := await reader.readline():
        if len(line) > 4096:
            continue
        try:
            event = ProgressEvent.model_validate_json(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if event.type == "progress":
            now = time.monotonic()
            changed = (event.stage, event.fraction) != (last_stage, last_fraction)
            boundary = event.fraction in {0.0, 1.0}
            if changed and (event.stage != last_stage or boundary or now - last_update >= 1):
                await service.update_progress(job_id, lease_token, event.stage, event.fraction)
                last_stage, last_fraction, last_update = event.stage, event.fraction, now


async def _drain_stderr(reader: asyncio.StreamReader | None, job_id: str) -> None:
    if reader is None:
        return
    while line := await reader.readline():
        if len(line) <= 4096:
            message = line.decode("utf-8", errors="replace").strip()
            if message:
                # Runner stderr is diagnostic only; keep it out of user-visible status.
                LOG.debug("runner stderr: %s", message, extra={"job_id": job_id})


async def run_worker(
    service: JobService,
    data_dir: Path,
    enabled_plugins: set[str],
    timeout_seconds: int = 300,
    assets_root: Path | None = None,
) -> None:
    """Claim one SQLite job at a time and render it in a token-free child process."""
    await service.recover_expired_leases()
    while True:
        job = await service.claim()
        if job is None:
            await asyncio.sleep(1)
            continue
        current_job = job
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        }
        workspace = data_dir / "results" / current_job.id
        workspace.mkdir(parents=True, exist_ok=True)
        input_path, output_path = workspace / "input.json", workspace / "result.json"
        input_path.write_text(
            RunnerInput(
                job_id=current_job.id,
                lease_token=current_job.lease_token or "",
                plugin_id=current_job.plugin_id,
                plugin_version=current_job.plugin_version,
                input_json=current_job.input_json,
                options_json=current_job.options_json,
                workspace=str(workspace),
            ).model_dump_json(),
            encoding="utf-8",
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "media_bot",
            "run-payload",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--plugins",
            ",".join(sorted(enabled_plugins)),
            *(["--assets-root", str(assets_root.resolve())] if assets_root is not None else []),
            env=environment,
            start_new_session=True,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        progress_task = asyncio.create_task(
            _drain_progress(process.stdout, service, job.id, job.lease_token or "")
        )
        stderr_task = asyncio.create_task(_drain_stderr(process.stderr, job.id))

        async def heartbeat(
            job_id: str = current_job.id, lease_token: str = current_job.lease_token or ""
        ) -> None:
            while True:
                await asyncio.sleep(5)
                if not await service.heartbeat(job_id, lease_token):
                    return

        heartbeat_task = asyncio.create_task(heartbeat())
        try:
            elapsed = 0
            cancelled = False
            while True:
                try:
                    exit_code = await asyncio.wait_for(process.wait(), timeout=1)
                    break
                except TimeoutError:
                    elapsed += 1
                    if await service.cancellation_requested(job.id, job.lease_token or ""):
                        os.killpg(process.pid, signal.SIGTERM)
                        await asyncio.sleep(2)
                        if process.returncode is None:
                            os.killpg(process.pid, signal.SIGKILL)
                        await process.wait()
                        await service.mark_cancelled(job.id, job.lease_token or "")
                        cancelled = True
                        break
                    if elapsed >= timeout_seconds:
                        raise TimeoutError from None
        except TimeoutError:
            os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            await service.fail(job.id, job.lease_token, "Render timed out")
        else:
            if cancelled:
                pass
            elif exit_code != 0:
                await service.fail(job.id, job.lease_token, f"Runner exited with code {exit_code}")
            else:
                try:
                    result = RunnerResult.model_validate_json(
                        output_path.read_text(encoding="utf-8")
                    )
                    suffixes = {".mp4"} if result.media_type == "video/mp4" else {".png", ".webp"}
                    artifact = validate_artifact(workspace, result.path, suffixes)
                    await service.complete(job.id, job.lease_token or "", str(artifact))
                except Exception as error:
                    await service.fail(job.id, job.lease_token, str(error))
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            await asyncio.gather(progress_task, stderr_task)
