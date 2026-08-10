"""Standalone CLI for backend endpoint checks, model inventory, and stress probes.

The suite is separate from the deployed Docker app. It loads configuration from
.env.example, .env, and the process environment; inventories every configured
external model API surface; and writes JSON/CSV reports under
api_model_suite/reports by default.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

try:
    from dotenv import dotenv_values
except Exception:  # pragma: no cover - fallback for very lean environments
    dotenv_values = None

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - fallback for environments before installing this suite
    tqdm = None


SUITE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SUITE_DIR.parent
DEFAULT_REPORT_DIR = SUITE_DIR / "reports"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
AUTH_OR_RATE_LIMIT_CODES = {401, 403, 429}

API_SURFACES = {
    "backend-chat",
    "direct-chat-completions",
    "direct-embeddings",
    "pipeline-stage",
}
FIXED_CHAT_MODELS = (
    ("openai/gpt-oss-20b", "FAST", 1500),
)


@dataclass(frozen=True)
class ModelInventoryItem:
    model_name: str
    provider: str
    api_surface: str
    role: str
    source: str
    max_tokens: int | None = None


@dataclass
class ResultRow:
    check: str
    status: str
    detail: str = ""
    model_name: str = ""
    provider: str = ""
    api_surface: str = ""
    role: str = ""
    source: str = ""
    status_code: int | None = None
    latency_ms: float | None = None
    response_bytes: int | None = None
    error_class: str = ""
    extra: dict[str, Any] | None = None


class SuiteContext:
    def __init__(
        self,
        *,
        env: dict[str, str],
        base_url: str,
        report_dir: Path,
        timeout_sec: float,
        verbose: bool,
        config_source: str,
    ) -> None:
        self.env = env
        self.base_url = base_url.rstrip("/")
        self.report_dir = report_dir
        self.timeout_sec = timeout_sec
        self.verbose = verbose
        self.config_source = config_source


class Progress:
    def __init__(self, ctx: SuiteContext, *, total: int, desc: str, unit: str = "check") -> None:
        self.ctx = ctx
        self.total = max(0, total)
        self.desc = desc
        self.unit = unit
        self.count = 0
        self._bar: Any = None

    def __enter__(self) -> "Progress":
        if tqdm is not None:
            self._bar = tqdm(total=self.total, desc=self.desc, unit=self.unit, dynamic_ncols=True, leave=True)
        else:
            print(f"{self.desc}: 0/{self.total} {self.unit}s")
        return self

    def advance(self, row: ResultRow | None = None) -> None:
        self.count += 1
        if self._bar is not None:
            if row and self.ctx.verbose:
                self._bar.set_postfix_str(f"{row.status}:{row.check}", refresh=False)
            self._bar.update(1)
            return

        if row:
            print(f"{self.desc}: {self.count}/{self.total} {row.status} {row.check}")
        else:
            print(f"{self.desc}: {self.count}/{self.total}")

    def status(self, message: str) -> None:
        if self._bar is not None:
            self._bar.set_postfix_str(message[:80], refresh=True)
        elif self.ctx.verbose:
            print(f"{self.desc}: {message}")

    def note(self, message: str) -> None:
        if self._bar is not None and tqdm is not None:
            tqdm.write(message)
        else:
            print(message)

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._bar is not None:
            self._bar.close()


def announce(ctx: SuiteContext, message: str) -> None:
    if not ctx.verbose:
        return
    if tqdm is not None:
        tqdm.write(message)
    else:
        print(message)


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_example = REPO_ROOT / ".env.example"
    env_file = REPO_ROOT / ".env"

    if dotenv_values:
        for path in (env_example, env_file):
            if path.exists():
                for key, value in dotenv_values(path).items():
                    if key and value is not None:
                        values[key] = str(value)
    else:
        for path in (env_example, env_file):
            if path.exists():
                values.update(_parse_env_file(path))

    values.update({key: value for key, value in os.environ.items() if isinstance(value, str)})
    return values


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip().strip("'\"")
        values[key.strip()] = value
    return values


def env_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def short_model_name(model_id: str) -> str:
    return model_id.split("/")[-1] if "/" in model_id else model_id


def is_remote_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    return host not in {"", "localhost", "127.0.0.1", "::1", "0.0.0.0"}


def effective_config_source(ctx: SuiteContext) -> str:
    if ctx.config_source != "auto":
        return ctx.config_source
    return "backend" if is_remote_base_url(ctx.base_url) else "hybrid"


def discover_models(env: dict[str, str]) -> list[ModelInventoryItem]:
    items: list[ModelInventoryItem] = []

    stage_specs = [
        ("EDGE_VERIFY", "edge_verify"),
        ("RISK_ANALYZER", "risk_analyzer"),
        ("FINAL_REPORT", "final_report"),
    ]
    for prefix, role in stage_specs:
        provider = env.get(f"{prefix}_PROVIDER", "nvidia").lower() or "nvidia"
        model = env.get(f"{prefix}_MODEL", "").strip()
        if model:
            items.append(
                ModelInventoryItem(
                    model_name=model,
                    provider=provider,
                    api_surface="pipeline-stage",
                    role=role,
                    source=f"{prefix}_MODEL",
                )
            )
        fallback_provider = env.get(f"{prefix}_FALLBACK_PROVIDER", provider).lower() or provider
        fallback_model = env.get(f"{prefix}_FALLBACK_MODEL", "").strip()
        if fallback_model:
            items.append(
                ModelInventoryItem(
                    model_name=fallback_model,
                    provider=fallback_provider,
                    api_surface="pipeline-stage",
                    role=f"{role}_fallback",
                    source=f"{prefix}_FALLBACK_MODEL",
                )
            )

    for model, attr, max_tokens in FIXED_CHAT_MODELS:
        role = f"chat_{attr.lower()}"
        items.append(
            ModelInventoryItem(
                model_name=model,
                provider="nvidia",
                api_surface="backend-chat",
                role=role,
                source="fixed_chat_catalog",
                max_tokens=max_tokens,
            )
        )
        items.append(
            ModelInventoryItem(
                model_name=model,
                provider="nvidia",
                api_surface="direct-chat-completions",
                role=role,
                source="fixed_chat_catalog",
                max_tokens=max_tokens,
            )
        )

    embedding_model = env.get("EMBEDDING_MODEL", "nvidia/nv-embed-v1").strip()
    if embedding_model:
        items.append(
            ModelInventoryItem(
                model_name=embedding_model,
                provider="nvidia",
                api_surface="direct-embeddings",
                role="embedding",
                source="EMBEDDING_MODEL",
            )
        )

    return _dedupe_inventory(items)


def _dedupe_inventory(items: Iterable[ModelInventoryItem]) -> list[ModelInventoryItem]:
    seen: set[tuple[str, str, str, str, str]] = set()
    unique: list[ModelInventoryItem] = []
    for item in items:
        key = (item.model_name, item.provider, item.api_surface, item.role, item.source)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def request_row(
    *,
    check: str,
    method: str,
    url: str,
    expected_status: set[int],
    timeout_sec: float,
    **kwargs: Any,
) -> ResultRow:
    start = time.perf_counter()
    try:
        response = requests.request(method, url, timeout=timeout_sec, **kwargs)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        status = "pass" if response.status_code in expected_status else "fail"
        return ResultRow(
            check=check,
            status=status,
            detail=response.text[:300],
            status_code=response.status_code,
            latency_ms=latency_ms,
            response_bytes=len(response.content or b""),
            error_class=classify_status(response.status_code),
        )
    except requests.RequestException as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return ResultRow(
            check=check,
            status="fail",
            detail=str(exc),
            latency_ms=latency_ms,
            error_class=exc.__class__.__name__,
        )


def classify_status(status_code: int | None) -> str:
    if status_code in (401, 403):
        return "auth"
    if status_code == 429:
        return "rate_limit"
    if status_code and status_code >= 500:
        return "server"
    if status_code and status_code >= 400:
        return "client"
    return ""


def check_backend(ctx: SuiteContext, *, pdf_path: Path | None = None, run_id: str | None = None) -> list[ResultRow]:
    steps = [
        lambda: request_row(
            check="backend.healthz",
            method="GET",
            url=f"{ctx.base_url}/healthz",
            expected_status={200},
            timeout_sec=ctx.timeout_sec,
        ),
        lambda: request_row(
            check="backend.chat_models",
            method="GET",
            url=f"{ctx.base_url}/api/chat/models",
            expected_status={200},
            timeout_sec=ctx.timeout_sec,
        ),
        lambda: request_row(
            check="backend.upload_validation_non_pdf",
            method="POST",
            url=f"{ctx.base_url}/api/upload",
            expected_status={400, 422},
            timeout_sec=ctx.timeout_sec,
            files={"file": ("not-a-pdf.txt", b"hello", "text/plain")},
        ),
        lambda: request_row(
            check="backend.status_missing_run",
            method="GET",
            url=f"{ctx.base_url}/api/status/__api_model_suite_missing__",
            expected_status={404},
            timeout_sec=ctx.timeout_sec,
        ),
        lambda: request_row(
            check="backend.results_missing_sections",
            method="GET",
            url=f"{ctx.base_url}/api/results/__api_model_suite_missing__/sections",
            expected_status={404},
            timeout_sec=ctx.timeout_sec,
        ),
        lambda: request_row(
            check="backend.cancel_missing_run",
            method="POST",
            url=f"{ctx.base_url}/api/cancel/__api_model_suite_missing__",
            expected_status={404},
            timeout_sec=ctx.timeout_sec,
        ),
    ]
    rows: list[ResultRow] = []
    with Progress(ctx, total=len(steps), desc="Backend checks") as progress:
        for index, step in enumerate(steps, start=1):
            progress.status(f"starting {index}/{len(steps)}")
            row = step()
            rows.append(row)
            progress.advance(row)

    if run_id:
        announce(ctx, "Testing backend chat stream with provided run id...")
        rows.append(check_chat_stream(ctx, run_id=run_id, model_id=None))
    else:
        rows.append(ResultRow(check="backend.chat_stream", status="skipped", detail="Pass --run-id to test chat streaming."))

    if pdf_path:
        announce(ctx, "Testing real PDF upload/status/cancel flow...")
        rows.extend(check_real_upload_flow(ctx, pdf_path))
    else:
        rows.append(ResultRow(check="backend.real_upload_flow", status="skipped", detail="Pass --pdf to test real upload/cancel flow."))

    return rows


def check_real_upload_flow(ctx: SuiteContext, pdf_path: Path) -> list[ResultRow]:
    if not pdf_path.exists():
        return [ResultRow(check="backend.real_upload_flow", status="fail", detail=f"PDF not found: {pdf_path}")]
    rows: list[ResultRow] = []
    start = time.perf_counter()
    try:
        with pdf_path.open("rb") as handle:
            response = requests.post(
                f"{ctx.base_url}/api/upload",
                timeout=ctx.timeout_sec,
                files={"file": (pdf_path.name, handle, "application/pdf")},
            )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        detail = response.text[:300]
        run_id = ""
        if response.ok:
            run_id = response.json().get("run_id", "")
        rows.append(
            ResultRow(
                check="backend.real_upload",
                status="pass" if response.status_code == 200 and run_id else "fail",
                detail=detail,
                status_code=response.status_code,
                latency_ms=latency_ms,
                response_bytes=len(response.content or b""),
            )
        )
        if not run_id:
            return rows
        rows.append(
            request_row(
                check="backend.real_upload_status",
                method="GET",
                url=f"{ctx.base_url}/api/status/{run_id}",
                expected_status={200},
                timeout_sec=ctx.timeout_sec,
            )
        )
        rows.append(
            request_row(
                check="backend.real_upload_cancel",
                method="POST",
                url=f"{ctx.base_url}/api/cancel/{run_id}",
                expected_status={200},
                timeout_sec=ctx.timeout_sec,
            )
        )
    except (OSError, requests.RequestException, ValueError) as exc:
        rows.append(ResultRow(check="backend.real_upload_flow", status="fail", detail=str(exc), error_class=exc.__class__.__name__))
    return rows


def check_chat_stream(ctx: SuiteContext, *, run_id: str, model_id: str | None) -> ResultRow:
    payload = {"messages": [{"role": "user", "content": "Summarize the contract in one sentence."}]}
    if model_id:
        payload["model_id"] = model_id
    row = request_row(
        check="backend.chat_stream",
        method="POST",
        url=f"{ctx.base_url}/api/chat/{run_id}/stream",
        expected_status={200},
        timeout_sec=ctx.timeout_sec,
        json=payload,
        stream=True,
    )
    if row.status == "pass" and row.detail:
        row.detail = "stream opened"
    return row


def check_models(ctx: SuiteContext, *, list_only: bool = False) -> list[ResultRow]:
    announce(ctx, "Discovering configured model inventory...")
    inventory, backend_rows = collect_model_inventory(ctx)
    if list_only:
        print_inventory(inventory)
        return backend_rows + [
            ResultRow(
                check="model.inventory",
                status="pass",
                detail=f"{len(inventory)} configured model surface rows",
                model_name=item.model_name,
                provider=item.provider,
                api_surface=item.api_surface,
                role=item.role,
                source=item.source,
            )
            for item in inventory
        ]

    rows = backend_rows + [
        ResultRow(
            check="model.inventory",
            status="pass",
            detail="discovered",
            model_name=item.model_name,
            provider=item.provider,
            api_surface=item.api_surface,
            role=item.role,
            source=item.source,
        )
        for item in inventory
    ]

    auth_blocked: set[str] = set()
    probed: set[tuple[str, str, str]] = set()
    probe_candidates = [item for item in (direct_probe_item(item) for item in inventory) if item]
    with Progress(ctx, total=len(probe_candidates), desc="Model probes", unit="model") as progress:
        for probe_item in probe_candidates:
            progress.status(f"{probe_item.role}: {short_model_name(probe_item.model_name)}")
            probe_key = (probe_item.provider, probe_item.model_name, probe_item.api_surface)
            if probe_key in probed:
                row = result_from_item(probe_item, "model.probe_skipped", "skipped", "Provider/model/API surface already probed.")
                rows.append(row)
                progress.advance(row)
                continue
            probed.add(probe_key)
            if probe_item.provider in auth_blocked:
                row = result_from_item(probe_item, "model.probe_skipped", "skipped", "Provider auth/rate limit already hit.")
                rows.append(row)
                progress.advance(row)
                continue
            row = probe_direct_model(ctx, probe_item)
            rows.append(row)
            if row.status_code in AUTH_OR_RATE_LIMIT_CODES:
                auth_blocked.add(probe_item.provider)
            progress.advance(row)
    return rows


def collect_model_inventory(ctx: SuiteContext) -> tuple[list[ModelInventoryItem], list[ResultRow]]:
    source = effective_config_source(ctx)
    local_inventory = discover_models(ctx.env) if source in {"local", "hybrid"} else []
    backend_inventory: list[ModelInventoryItem] = []
    backend_rows: list[ResultRow] = []

    if source in {"backend", "hybrid"}:
        backend_inventory, backend_rows = discover_backend_chat_models(ctx)

    inventory = _dedupe_inventory([*local_inventory, *backend_inventory])
    backend_rows.insert(
        0,
        ResultRow(
            check="model.config_source",
            status="pass",
            detail=(
                f"config_source={source}. "
                "For remote deployments, backend source only includes models exposed by /api/chat/models; "
                "private HF pipeline env vars are not externally visible."
            ),
        ),
    )
    return inventory, backend_rows


def discover_backend_chat_models(ctx: SuiteContext) -> tuple[list[ModelInventoryItem], list[ResultRow]]:
    start = time.perf_counter()
    try:
        response = requests.get(f"{ctx.base_url}/api/chat/models", timeout=ctx.timeout_sec)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        row = ResultRow(
            check="model.backend_inventory",
            status="pass" if response.status_code == 200 else "fail",
            detail=response.text[:300],
            status_code=response.status_code,
            latency_ms=latency_ms,
            response_bytes=len(response.content or b""),
            error_class=classify_status(response.status_code),
        )
        if response.status_code != 200:
            return [], [row]
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return [], [
            ResultRow(
                check="model.backend_inventory",
                status="skipped",
                detail=f"Could not read backend model inventory from {ctx.base_url}: {exc}",
                latency_ms=latency_ms,
                error_class=exc.__class__.__name__,
            )
        ]

    items: list[ModelInventoryItem] = []
    for model in payload.get("models", []):
        if not isinstance(model, dict):
            continue
        model_name = str(model.get("model") or "").strip()
        if not model_name:
            continue
        attribute = str(model.get("attribute") or "STANDARD").lower()
        items.append(
            ModelInventoryItem(
                model_name=model_name,
                provider="nvidia",
                api_surface="backend-chat",
                role=f"chat_{attribute}",
                source="/api/chat/models",
                max_tokens=env_int(str(model.get("max_tokens") or ""), 0) or None,
            )
        )
    row.detail = f"loaded {len(items)} backend chat model rows"
    return items, [row]


def direct_probe_item(item: ModelInventoryItem) -> ModelInventoryItem | None:
    if item.api_surface == "direct-embeddings":
        return item
    if item.api_surface in {"pipeline-stage", "direct-chat-completions"}:
        return ModelInventoryItem(
            model_name=item.model_name,
            provider=item.provider,
            api_surface="direct-chat-completions",
            role=item.role,
            source=item.source,
            max_tokens=item.max_tokens,
        )
    return None


def result_from_item(item: ModelInventoryItem, check: str, status: str, detail: str) -> ResultRow:
    return ResultRow(
        check=check,
        status=status,
        detail=detail,
        model_name=item.model_name,
        provider=item.provider,
        api_surface=item.api_surface,
        role=item.role,
        source=item.source,
    )


def probe_direct_model(ctx: SuiteContext, item: ModelInventoryItem) -> ResultRow:
    api_key = provider_api_key(ctx.env, item.provider)
    if not api_key or api_key.startswith("replace-me"):
        return result_from_item(item, "model.probe", "skipped", f"Missing API key for provider {item.provider}.")

    if item.api_surface == "direct-embeddings":
        return probe_embedding(ctx, item, api_key)
    return probe_chat_completion(ctx, item, api_key)


def provider_api_key(env: dict[str, str], provider: str) -> str:
    if provider.lower() == "openai":
        return env.get("OPENAI_API_KEY", "")
    return env.get("NVIDIA_API_KEY", "")


def provider_base_url(provider: str) -> str:
    return OPENAI_BASE_URL if provider.lower() == "openai" else NVIDIA_BASE_URL


def probe_chat_completion(ctx: SuiteContext, item: ModelInventoryItem, api_key: str) -> ResultRow:
    payload = {
        "model": item.model_name,
        "messages": [
            {"role": "system", "content": "Reply with exactly: ok"},
            {"role": "user", "content": "health check"},
        ],
        "temperature": 0,
        "max_tokens": min(item.max_tokens or 32, 32),
    }
    return provider_post(ctx, item, "model.probe_chat", f"{provider_base_url(item.provider)}/chat/completions", payload, api_key)


def probe_embedding(ctx: SuiteContext, item: ModelInventoryItem, api_key: str) -> ResultRow:
    payload = {
        "model": item.model_name,
        "input": ["contract api health check"],
        "encoding_format": "float",
    }
    if item.provider.lower() == "nvidia":
        payload["input_type"] = "query"
        payload["truncate"] = "END"
    return provider_post(ctx, item, "model.probe_embedding", f"{provider_base_url(item.provider)}/embeddings", payload, api_key)


def provider_post(ctx: SuiteContext, item: ModelInventoryItem, check: str, url: str, payload: dict[str, Any], api_key: str) -> ResultRow:
    start = time.perf_counter()
    try:
        response = requests.post(
            url,
            timeout=ctx.timeout_sec,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        detail = response.text[:300]
        status = "pass" if 200 <= response.status_code < 300 else "fail"
        return ResultRow(
            check=check,
            status=status,
            detail=detail,
            model_name=item.model_name,
            provider=item.provider,
            api_surface=item.api_surface,
            role=item.role,
            source=item.source,
            status_code=response.status_code,
            latency_ms=latency_ms,
            response_bytes=len(response.content or b""),
            error_class=classify_status(response.status_code),
        )
    except requests.RequestException as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return ResultRow(
            check=check,
            status="fail",
            detail=str(exc),
            model_name=item.model_name,
            provider=item.provider,
            api_surface=item.api_surface,
            role=item.role,
            source=item.source,
            latency_ms=latency_ms,
            error_class=exc.__class__.__name__,
        )


def run_stress(ctx: SuiteContext, *, requests_count: int, concurrency: int, run_id: str | None) -> list[ResultRow]:
    announce(ctx, f"Starting stress run: requests={requests_count}, concurrency={concurrency}")
    model_inventory, inventory_rows = collect_model_inventory(ctx)
    inventory = _dedupe_probe_items([item for item in (direct_probe_item(item) for item in model_inventory) if item])
    rows: list[ResultRow] = []
    rows.extend(inventory_rows)
    auth_or_rate_limit_hits = 0

    def task(index: int) -> ResultRow:
        if index % 3 == 0:
            return request_row(
                check="stress.backend.chat_models",
                method="GET",
                url=f"{ctx.base_url}/api/chat/models",
                expected_status={200},
                timeout_sec=ctx.timeout_sec,
            )
        if index % 3 == 1:
            return request_row(
                check="stress.backend.healthz",
                method="GET",
                url=f"{ctx.base_url}/healthz",
                expected_status={200},
                timeout_sec=ctx.timeout_sec,
            )
        if run_id and index % 5 == 0:
            return check_chat_stream(ctx, run_id=run_id, model_id=None)
        if not inventory:
            return ResultRow(check="stress.model_probe", status="skipped", detail="No configured model inventory.")
        return probe_direct_model(ctx, inventory[index % len(inventory)])

    max_workers = max(1, concurrency)
    next_index = 0
    pending = set()
    with Progress(ctx, total=max(0, requests_count), desc="Stress requests", unit="req") as progress:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while next_index < max(0, requests_count) and len(pending) < max_workers:
                pending.add(executor.submit(task, next_index))
                next_index += 1

            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    row = future.result()
                    rows.append(row)
                    if row.status_code in AUTH_OR_RATE_LIMIT_CODES:
                        auth_or_rate_limit_hits += 1
                    progress.advance(row)

                if auth_or_rate_limit_hits >= 3:
                    for future in pending:
                        future.cancel()
                    rows.append(ResultRow(check="stress.early_stop", status="skipped", detail="Stopped after repeated auth/rate-limit responses."))
                    progress.note("Stress stopped early after repeated auth/rate-limit responses.")
                    break

                while next_index < max(0, requests_count) and len(pending) < max_workers:
                    pending.add(executor.submit(task, next_index))
                    next_index += 1

    rows.append(stress_summary(rows))
    return rows


def _dedupe_probe_items(items: list[ModelInventoryItem]) -> list[ModelInventoryItem]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ModelInventoryItem] = []
    for item in items:
        key = (item.provider, item.model_name, item.api_surface)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def stress_summary(rows: list[ResultRow]) -> ResultRow:
    latencies = sorted(row.latency_ms for row in rows if row.latency_ms is not None)
    total = len([row for row in rows if not row.check.endswith("summary")])
    failures = len([row for row in rows if row.status == "fail"])
    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)
    return ResultRow(
        check="stress.summary",
        status="pass" if failures == 0 else "fail",
        detail=f"total={total} failures={failures} p50_ms={p50} p95_ms={p95}",
        extra={"total": total, "failures": failures, "p50_ms": p50, "p95_ms": p95},
    )


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    index = min(len(values) - 1, max(0, round((len(values) - 1) * fraction)))
    return values[index]


def print_inventory(inventory: list[ModelInventoryItem]) -> None:
    headers = ["model_name", "provider", "api_surface", "role", "source", "max_tokens"]
    rows = [[getattr(item, header) or "" for header in headers] for item in inventory]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def write_reports(rows: list[ResultRow], report_dir: Path, prefix: str) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int((time.time() % 1) * 1000):03d}"
    json_path = report_dir / f"{prefix}-{timestamp}.json"
    csv_path = report_dir / f"{prefix}-{timestamp}.csv"
    payload = [row_to_dict(row) for row in rows]
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fields = [
        "check",
        "status",
        "detail",
        "model_name",
        "provider",
        "api_surface",
        "role",
        "source",
        "status_code",
        "latency_ms",
        "response_bytes",
        "error_class",
        "extra",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(payload)
    return json_path, csv_path


def row_to_dict(row: ResultRow) -> dict[str, Any]:
    data = asdict(row)
    data["extra"] = json.dumps(data["extra"] or {}, sort_keys=True)
    return data


def print_summary(rows: list[ResultRow], *, report_paths: tuple[Path, Path] | None = None) -> int:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    print("Summary:", ", ".join(f"{status}={count}" for status, count in sorted(counts.items())) or "no rows")
    failures = [row for row in rows if row.status == "fail"]
    for row in failures[:10]:
        suffix = f" ({row.status_code})" if row.status_code else ""
        print(f"FAIL {row.check}{suffix}: {row.detail[:160]}")
    if report_paths:
        print(f"JSON report: {report_paths[0]}")
        print(f"CSV report:  {report_paths[1]}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    description = """
Standalone Legal Sentinel API/model verification suite.

The CLI checks the FastAPI backend, inventories configured external API model
surfaces, sends tiny direct provider probes, and can run a bounded stress
simulation. Configuration is loaded from .env.example, then .env, then the
process environment. Direct NVIDIA calls require NVIDIA_API_KEY; OpenAI provider
calls require OPENAI_API_KEY. Reports are written to api_model_suite/reports by
default.
""".strip()
    parser = argparse.ArgumentParser(
        prog="python -m api_model_suite",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"FastAPI backend base URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Directory for JSON/CSV reports.")
    parser.add_argument("--timeout-sec", type=float, default=60.0, help="HTTP timeout per request.")
    parser.add_argument("--verbose", action="store_true", help="Print additional details while running.")
    parser.add_argument(
        "--config-source",
        choices=("auto", "backend", "local", "hybrid"),
        default="auto",
        help=(
            "Model inventory source. auto uses backend-only for remote base URLs and hybrid for localhost. "
            "backend reads /api/chat/models only; local reads .env/environment only; hybrid combines both."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    backend = subparsers.add_parser(
        "check-backend",
        help="Verify backend health, model listing, validation, missing-run, cancel, and optional upload flow.",
        description="""
Verify the FastAPI backend over HTTP.

Examples:
  python -m api_model_suite check-backend
  python -m api_model_suite check-backend --pdf ./sample.pdf
  python -m api_model_suite check-backend --run-id abc123
""".strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_subcommand_args(backend)
    backend.add_argument("--pdf", type=Path, help="Optional PDF path for a real upload/status/cancel flow.")
    backend.add_argument("--run-id", help="Existing completed run id for backend chat stream verification.")

    models = subparsers.add_parser(
        "check-models",
        help="Inventory configured models and optionally send tiny direct provider probes.",
        description="""
Discover configured models from .env/environment and show their external API
surface, provider, model_name, role, and source. Use --list to avoid API calls.

Examples:
  python -m api_model_suite check-models --list
  NVIDIA_API_KEY=... python -m api_model_suite check-models
""".strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_subcommand_args(models)
    models.add_argument("--list", action="store_true", help="Print model inventory without making direct API calls.")

    stress = subparsers.add_parser(
        "stress",
        help="Run moderate bounded concurrency against backend endpoints and direct model probes.",
        description="""
Run a simple bounded stress simulation. Defaults are intentionally moderate:
20 total requests, concurrency 4, 60 second per-request timeout.

Examples:
  python -m api_model_suite stress
  python -m api_model_suite stress --requests 3 --concurrency 2
  python -m api_model_suite stress --run-id abc123
""".strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_subcommand_args(stress)
    stress.add_argument("--requests", type=int, default=20, help="Total stress requests to schedule. Default: 20.")
    stress.add_argument("--concurrency", type=int, default=4, help="Maximum concurrent workers. Default: 4.")
    stress.add_argument("--run-id", help="Existing completed run id for including backend chat stream stress calls.")

    all_cmd = subparsers.add_parser(
        "all",
        help="Run backend checks, model checks, then stress.",
        description="""
Run check-backend, check-models, and stress in sequence.

Examples:
  python -m api_model_suite all
  python -m api_model_suite all --pdf ./sample.pdf --requests 3 --concurrency 2
""".strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_subcommand_args(all_cmd)
    all_cmd.add_argument("--pdf", type=Path, help="Optional PDF path for backend real upload flow.")
    all_cmd.add_argument("--run-id", help="Existing completed run id for backend chat stream verification.")
    all_cmd.add_argument("--requests", type=int, default=20, help="Total stress requests to schedule. Default: 20.")
    all_cmd.add_argument("--concurrency", type=int, default=4, help="Maximum concurrent workers. Default: 4.")
    return parser


def add_common_subcommand_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=argparse.SUPPRESS, help=f"FastAPI backend base URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--report-dir", type=Path, default=argparse.SUPPRESS, help="Directory for JSON/CSV reports.")
    parser.add_argument("--timeout-sec", type=float, default=argparse.SUPPRESS, help="HTTP timeout per request.")
    parser.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS, help="Print additional details while running.")
    parser.add_argument(
        "--config-source",
        choices=("auto", "backend", "local", "hybrid"),
        default=argparse.SUPPRESS,
        help="Model inventory source. Use hybrid to include local .env stage models during remote runs.",
    )


def context_from_args(args: argparse.Namespace) -> SuiteContext:
    return SuiteContext(
        env=load_env(),
        base_url=args.base_url,
        report_dir=args.report_dir,
        timeout_sec=args.timeout_sec,
        verbose=args.verbose,
        config_source=args.config_source,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = context_from_args(args)

    if args.command == "check-backend":
        announce(ctx, "Running check-backend...")
        rows = check_backend(ctx, pdf_path=args.pdf, run_id=args.run_id)
        paths = write_reports(rows, ctx.report_dir, "check-backend")
        return print_summary(rows, report_paths=paths)

    if args.command == "check-models":
        announce(ctx, "Running check-models...")
        rows = check_models(ctx, list_only=args.list)
        paths = write_reports(rows, ctx.report_dir, "check-models")
        return print_summary(rows, report_paths=paths)

    if args.command == "stress":
        announce(ctx, "Running stress...")
        rows = run_stress(ctx, requests_count=args.requests, concurrency=args.concurrency, run_id=args.run_id)
        paths = write_reports(rows, ctx.report_dir, "stress")
        return print_summary(rows, report_paths=paths)

    if args.command == "all":
        rows: list[ResultRow] = []
        announce(ctx, "Running all: backend checks...")
        rows.extend(check_backend(ctx, pdf_path=args.pdf, run_id=args.run_id))
        announce(ctx, "Running all: model checks...")
        rows.extend(check_models(ctx, list_only=False))
        announce(ctx, "Running all: stress...")
        rows.extend(run_stress(ctx, requests_count=args.requests, concurrency=args.concurrency, run_id=args.run_id))
        paths = write_reports(rows, ctx.report_dir, "all")
        return print_summary(rows, report_paths=paths)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
