import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from openai import OpenAI

from .config import Settings, StageConfig
from .io_utils import extract_all_json_candidates
from .key_pool import get_nvidia_key_pool, is_retryable_error


def _execute_single_call(
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    response_format: Optional[dict[str, str]],
    timeout: int
) -> str:
    """Executes a single API call strictly to the active provider backend."""
    if provider.lower() == "nvidia":
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            timeout=timeout,
            # The application owns retry/cooldown policy. SDK retries can multiply a
            # single stage timeout and leave a synchronous pipeline looking stuck.
            max_retries=0,
        )
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            # NVIDIA uses OpenAI SDK
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
        
    elif provider.lower() == "openai":
        client = OpenAI(api_key=api_key, timeout=timeout, max_retries=0)
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
        
    else:
        raise ValueError(f"Unknown provider: {provider}")

def _write_trace(
    settings: Settings,
    stage_name: str,
    trace_id: str,
    role: str,
    provider: str,
    model: str,
    messages: list,
    raw_output: str,
    extracted_json: Optional[dict],
    parse_status: str,
    validation_error: str,
    duration: float,
    response_format: Optional[dict] = None
):
    if not settings.debug_traceflow:
        return
        
    trace_dir = os.path.join(settings.out_dir, "traces", stage_name.lower())
    os.makedirs(trace_dir, exist_ok=True)
    
    timestamp = int(time.time() * 1000)
    status_tag = "success" if not validation_error and (not extracted_json or parse_status != "invalid") else "failed"
    safe_trace_id = "".join([c if c.isalnum() else "_" for c in trace_id])
    safe_mdl = "".join([c if c.isalnum() else "_" for c in model])
    
    filename = f"{timestamp}_{safe_trace_id}_{role}_{safe_mdl}_{status_tag}.json"
    filepath = os.path.join(trace_dir, filename)
    
    payload = {
        "timestamp": timestamp,
        "stage": stage_name,
        "trace_id": trace_id,
        "role": role,
        "provider": provider,
        "model": model,
        "duration_sec": round(duration, 3),
        "messages": messages,
        "raw_output": raw_output,
        "extracted_json": extracted_json,
        "parse_status": parse_status,
        "validation_error": validation_error,
        "response_format_used": response_format
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def execute_with_fallback(
    stage_name: str,
    trace_id: str,
    stage_config: StageConfig,
    settings: Settings,
    messages: list[dict[str, Any]],
    temperature: float = 0.0,
    max_tokens: int = 1500,
    response_format: Optional[dict[str, str]] = None,
    validator_fn: Optional[Callable[[dict], None]] = None,
    return_raw_on_parse_error: bool = False,
    timeout_sec: Optional[int] = None,
    max_retries: Optional[int] = None,
    race_nvidia_keys: bool = False,
) -> tuple[str, Optional[dict]]:
    """
    Higher-level loop orchestrating fallback execution, validation hooking, and tracing.
    Returns (raw_string, parsed_valid_dict).
    If validation fails completely (including fallback), throws RuntimeError.
    """
    
    def attempt_call(role: str, pvdr: str, key: str, mdl: str) -> tuple[str, Optional[dict]]:
        start_time = time.time()
        raw_output = ""
        extracted = None
        parse_status = "N/A"
        val_error = ""
        
        print(f"🤖 [{stage_name}] Calling {role} model: {mdl} (Trace ID: {trace_id})")
        
        try:
            if pvdr.lower() == "nvidia":
                pool = get_nvidia_key_pool(settings)
                failures = []
                request_timeout = timeout_sec or settings.llm_timeout_sec
                retry_limit = settings.llm_max_retries if max_retries is None else max_retries
                if race_nvidia_keys:
                    # The report is a single, independent request. Race it across
                    # available slots and return the first completed valid response.
                    # Do not use this for every risk batch: that would multiply cost.
                    max_racers = getattr(settings, "final_report_race_keys", 0) or pool.size
                    max_racers = max(1, min(pool.size, max_racers))

                    def race_call() -> tuple[str, int]:
                        lease = pool.acquire(request_timeout)
                        try:
                            output = _execute_single_call(
                                pvdr, lease.key, mdl, messages, temperature,
                                max_tokens, response_format, request_timeout,
                            )
                        except Exception as exc:
                            pool.release(lease, retryable_failure=is_retryable_error(exc))
                            raise RuntimeError(f"slot {lease.slot}: {exc}") from exc
                        pool.release(lease)
                        if not output or not output.strip():
                            raise ValueError(f"slot {lease.slot}: Model returned empty output")
                        return output, lease.slot

                    executor = ThreadPoolExecutor(max_workers=max_racers)
                    futures = [executor.submit(race_call) for _ in range(max_racers)]
                    try:
                        for future in as_completed(futures):
                            try:
                                raw_output, winner_slot = future.result()
                                print(f"🏁 [{stage_name}] First completed NVIDIA response won from slot {winner_slot}")
                                break
                            except Exception as exc:
                                failures.append(str(exc))
                        else:
                            raise RuntimeError("; ".join(failures))
                    finally:
                        for future in futures:
                            future.cancel()
                        # Requests already in flight cannot be interrupted by the
                        # OpenAI SDK, but they no longer block the pipeline result.
                        executor.shutdown(wait=False, cancel_futures=True)
                else:
                    for _ in range(retry_limit + 1):
                        lease = pool.acquire(request_timeout)
                        try:
                            raw_output = _execute_single_call(pvdr, lease.key, mdl, messages, temperature, max_tokens, response_format, request_timeout)
                            pool.release(lease)
                            break
                        except Exception as exc:
                            retryable = is_retryable_error(exc)
                            pool.release(lease, retryable_failure=retryable)
                            failures.append(f"slot {lease.slot}: {exc}")
                            if not retryable:
                                raise
                    else:
                        raise RuntimeError("; ".join(failures))
            else:
                raw_output = _execute_single_call(
                    pvdr,
                    key,
                    mdl,
                    messages,
                    temperature,
                    max_tokens,
                    response_format,
                    timeout_sec or getattr(settings, "llm_timeout_sec", 60),
                )
            
            if not raw_output or not raw_output.strip():
                raise ValueError("Model returned empty output")
                
            if (response_format and response_format.get("type") == "json_object") or validator_fn:
                candidates = extract_all_json_candidates(raw_output)
                if not candidates:
                    raise ValueError("No valid JSON structures found in output")
                    
                valid_candidate = None
                last_val_err = "No JSON candidates provided."
                
                # Check candidates in reverse so we favor the last match
                for cand_dict, cand_status in reversed(candidates):
                    if validator_fn:
                        try:
                            validator_fn(cand_dict)
                            valid_candidate = cand_dict
                            parse_status = cand_status
                            break
                        except Exception as e:
                            last_val_err = str(e)
                    else:
                        valid_candidate = cand_dict
                        parse_status = cand_status
                        break
                        
                if valid_candidate is None:
                    if return_raw_on_parse_error:
                        _write_trace(settings, stage_name, trace_id, role, pvdr, mdl, messages, raw_output, extracted, parse_status, f"Schema validation failed: {last_val_err}", time.time() - start_time, response_format)
                        return raw_output, None
                    raise ValueError(f"Schema validation failed on all candidates. Last error: {last_val_err}")
                    
                extracted = valid_candidate
                
        except Exception as e:
            val_error = str(e)
            _write_trace(settings, stage_name, trace_id, role, pvdr, mdl, messages, raw_output, extracted, parse_status, val_error, time.time() - start_time, response_format)
            raise RuntimeError(val_error) from e
            
        _write_trace(settings, stage_name, trace_id, role, pvdr, mdl, messages, raw_output, extracted, parse_status, val_error, time.time() - start_time, response_format)
        return raw_output, extracted

    def provider_key(provider: str) -> str:
        if provider.lower() == "nvidia":
            return settings.nvidia_api_key
        if provider.lower() == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        raise ValueError(f"Unknown provider: {provider}")

    # Attempt Primary
    try:
        return attempt_call("primary", stage_config.provider, provider_key(stage_config.provider), stage_config.model)
    except Exception as e:
        primary_err = str(e)
        if stage_config.fallback_model:
            print(f"⚠️ {stage_name} ({trace_id}) primary failed ({primary_err}). Triggering fallback.")
            try:
                # Attempt Fallback
                return attempt_call(
                    "fallback", 
                    stage_config.fallback_provider or stage_config.provider, 
                    provider_key(stage_config.fallback_provider or stage_config.provider),
                    stage_config.fallback_model
                )
            except Exception as fe:
                raise RuntimeError(f"Fallback exhausted. Primary Err: {primary_err} | Fallback Err: {str(fe)}")
        else:
            raise RuntimeError(f"Primary failed and no fallback configured: {primary_err}")
