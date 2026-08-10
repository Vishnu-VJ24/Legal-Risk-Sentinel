import json
import time
import traceback
from typing import Any, Dict, List

from openai import OpenAI

from .retrieval import is_contract_query, retrieve_context

DEFAULT_CHAT_MODEL = "openai/gpt-oss-20b"


def _estimate_tokens(text: str) -> int:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return max(1, round(len(cleaned) / 4))


class ThinkStreamParser:
    def __init__(self):
        self._buffer = ""
        self._in_think = False

    @staticmethod
    def _safe_prefix_split(text: str, tag: str) -> tuple[str, str]:
        max_hold = min(len(text), len(tag) - 1)
        for size in range(max_hold, 0, -1):
            if text.endswith(tag[:size]):
                return text[:-size], text[-size:]
        return text, ""

    def process(self, text: str, emit_tag_reasoning: bool) -> tuple[str, str]:
        self._buffer += text
        visible_parts: list[str] = []
        reasoning_parts: list[str] = []

        while self._buffer:
            if self._in_think:
                close_idx = self._buffer.find("</think>")
                if close_idx == -1:
                    safe_text, remainder = self._safe_prefix_split(self._buffer, "</think>")
                    if emit_tag_reasoning and safe_text:
                        reasoning_parts.append(safe_text)
                    self._buffer = remainder
                    break

                think_text = self._buffer[:close_idx]
                if emit_tag_reasoning and think_text:
                    reasoning_parts.append(think_text)
                self._buffer = self._buffer[close_idx + len("</think>"):]
                self._in_think = False
                continue

            open_idx = self._buffer.find("<think>")
            if open_idx == -1:
                safe_text, remainder = self._safe_prefix_split(self._buffer, "<think>")
                if safe_text:
                    visible_parts.append(safe_text)
                self._buffer = remainder
                break

            if open_idx > 0:
                visible_parts.append(self._buffer[:open_idx])
            self._buffer = self._buffer[open_idx + len("<think>"):]
            self._in_think = True

        return "".join(visible_parts), "".join(reasoning_parts)

    def flush(self, emit_tag_reasoning: bool) -> tuple[str, str]:
        if not self._buffer:
            return "", ""

        remaining = self._buffer
        self._buffer = ""

        if self._in_think:
            self._in_think = False
            return "", remaining if emit_tag_reasoning else ""

        return remaining, ""

def stream_chat_impl(
    run_id: str,
    out_dir: str,
    messages: List[Dict[str, str]],
    api_key: str,
    model: str = DEFAULT_CHAT_MODEL,
    model_attribute: str = "FAST",
    max_tokens: int = 1500,
):
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )

    def emit(event: str, data: Any):
        # We stringify the payload. The SSE standard calls for data: <string>\n\n
        payload = json.dumps({"event": event, "data": data})
        return f"data: {payload}\n\n"

    def _extract_reasoning_delta(delta: Any) -> str | None:
        """
        vLLM/OpenAI-compatible backends may expose reasoning tokens under either
        `reasoning_content` or `reasoning` depending on version/model parser.
        """
        if delta is None:
            return None

        for attr in ("reasoning_content", "reasoning"):
            value = getattr(delta, attr, None)
            if isinstance(value, str) and value:
                return value

        return None

    def _extract_usage(chunk: Any) -> dict[str, int] | None:
        usage = getattr(chunk, "usage", None)
        if usage is None:
            return None

        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if prompt_tokens is None and completion_tokens is None and total_tokens is None:
            return None

        return {
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
        }

    def _emit_model_stats(
        *,
        started_at: float,
        first_token_at: float | None,
        finished_at: float,
        finish_reason: str | None,
        visible_text: str,
        reasoning_text: str,
        context_items: int,
        usage: dict[str, int] | None,
        direct_retry_used: bool,
    ):
        output_tokens_exact = usage["completion_tokens"] if usage and usage.get("completion_tokens") else None
        output_tokens_estimated = _estimate_tokens(visible_text)
        reasoning_tokens_estimated = _estimate_tokens(reasoning_text)
        output_tokens = output_tokens_exact or output_tokens_estimated
        total_time_sec = max(finished_at - started_at, 0.0)
        ttft_sec = max((first_token_at or finished_at) - started_at, 0.0)
        generation_window_sec = max(finished_at - (first_token_at or started_at), 0.001)
        tps = round(output_tokens / generation_window_sec, 2) if output_tokens > 0 else 0.0

        stats = {
            "provider": "nvidia",
            "model": model,
            "model_attribute": model_attribute.upper(),
            "max_tokens_configured": max_tokens,
            "finish_reason": finish_reason or "unknown",
            "retrieved_context_items": context_items,
            "used_direct_answer_retry": direct_retry_used,
            "ttft_sec": round(ttft_sec, 2),
            "total_time_sec": round(total_time_sec, 2),
            "tokens_per_second": tps,
            "output_tokens": output_tokens,
            "output_tokens_estimated": output_tokens_exact is None,
            "reasoning_tokens_estimated": reasoning_tokens_estimated,
            "visible_chars": len(visible_text),
            "reasoning_chars": len(reasoning_text),
        }
        if usage:
            stats["prompt_tokens"] = usage.get("prompt_tokens", 0)
            stats["completion_tokens"] = usage.get("completion_tokens", 0)
            stats["total_tokens"] = usage.get("total_tokens", 0)
            stats["usage_is_exact"] = True
        else:
            stats["usage_is_exact"] = False
            stats["prompt_tokens"] = _estimate_tokens(system_msg + "\n".join(m.get("content", "") for m in valid_messages))
            stats["completion_tokens"] = output_tokens + reasoning_tokens_estimated
            stats["total_tokens"] = stats["prompt_tokens"] + stats["completion_tokens"]

        yield emit("model_stats", stats)

    try:
        if not messages:
            yield emit("error", "No messages provided.")
            return

        user_query = messages[-1].get("content", "")
        
        # 1. RAG Retrieve
        context_str = ""
        metadata = []
        if is_contract_query(user_query):
            yield emit("status", "Searching contract artifacts...")
            context_str, metadata = retrieve_context(run_id, out_dir, user_query, api_key)
            
        if metadata:
            yield emit("metadata", metadata)

        # 2. Build system prompt
        # Defining a persona that balances precision with helpfulness
        ROLE_DEFINITION = (
            "You are a knowledgeable Legal Research Assistant specializing in contract analysis. "
            "Your goal is to provide thorough, evidence-based answers using the provided contract context."
        )
        reasoning_directive = ""
        if model_attribute.upper() == "THINKING":
            reasoning_directive = (
                "\n8. **Reasoning Budget**: Keep internal reasoning concise and move quickly to the final answer. "
                "Prioritize the visible answer over extended hidden deliberation."
            )

        if context_str:
            system_msg = (
                f"{ROLE_DEFINITION}\n\n"
                "### CONTEXT FROM CONTRACT:\n"
                "---"
                f"\n{context_str}\n"
                "---\n\n"
                "### OPERATIONAL DIRECTIVES:\n"
                "1. **Use All Available Context**: Analyze ALL the provided context segments thoroughly. "
                "Draw on every relevant piece of information, including directly referenced sections, "
                "risk analyses, related clauses, and report excerpts. Synthesize information from multiple "
                "segments when they relate to the same topic.\n"
                "2. **Citations**: Support your analysis with specific references. Use the format: (Section X.X) "
                "or cite the clause heading when available.\n"
                "3. **Risk & Obligations**: When the context includes risk analysis data, incorporate it into your "
                "answer — mention risk type, severity, and the rationale.\n"
                "4. **No Outside Knowledge**: Do not fabricate information not present in the context. "
                "If the context is partial, explain what IS available and what may be in other sections.\n"
                "5. **Helpful When Incomplete**: If you cannot fully answer from the provided context, "
                "still provide what you can, then suggest the user try:\n"
                "   - Asking about a specific clause by its full name\n"
                "   - Asking about related sections that appear in cross-references\n"
                "   - Rephrasing the question to focus on a specific risk or obligation\n"
                "6. **Formatting**: Use bolding for key terms and bullet points for lists of obligations or risks.\n"
                "7. **Decline Legal Advice**: Do not provide subjective legal opinions. Focus on what the text says."
                f"{reasoning_directive}\n\n"
                "Please analyze the user's request thoroughly using all provided context."
            )
        else:
            # Handling cases where the retriever fails to find relevant chunks
            system_msg = (
                f"{ROLE_DEFINITION}\n\n"
                "NOTICE: No specific contract segments were retrieved for this query. "
                "Please inform the user that the search didn't find closely matching content, "
                "and suggest they try:\n"
                "- Using the specific section number (e.g., 'explain section 2.2')\n"
                "- Asking about a topic like 'termination clauses' or 'risk allocation'\n"
                "- Referencing specific clause names from the contract\n"
                f"{reasoning_directive}\n"
                "Be helpful and guide them toward a productive query."
            )

        # Insert system msg
        # We should only keep user/assistant roles.
        valid_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") in ("user", "assistant")]
        prompt_messages = [{"role": "system", "content": system_msg}] + valid_messages
        
        yield emit("status", "Generating response...")

        # 3. Stream from LLM
        started_at = time.perf_counter()
        first_token_at: float | None = None
        usage: dict[str, int] | None = None
        direct_retry_used = False
        full_visible_text_parts: list[str] = []
        full_reasoning_parts: list[str] = []
        response = client.chat.completions.create(
            model=model,
            messages=prompt_messages,
            stream=True,
            temperature=0.3,
            max_tokens=max_tokens
        )
        parser = ThinkStreamParser()
        structured_reasoning_seen = False
        visible_char_count = 0
        reasoning_char_count = 0
        finish_reason = None

        for chunk in response:
            if not chunk.choices:
                continue

            finish_reason = getattr(chunk.choices[0], "finish_reason", finish_reason)
            usage = _extract_usage(chunk) or usage
            delta = chunk.choices[0].delta
            reasoning_delta = _extract_reasoning_delta(delta)
            if reasoning_delta is not None:
                structured_reasoning_seen = True
                reasoning_char_count += len(reasoning_delta)
                full_reasoning_parts.append(reasoning_delta)
                yield emit("reasoning", reasoning_delta)

            content_delta = delta.content if delta else None
            if content_delta is not None:
                visible_text, tagged_reasoning = parser.process(
                    content_delta,
                    emit_tag_reasoning=not structured_reasoning_seen
                )
                if tagged_reasoning:
                    reasoning_char_count += len(tagged_reasoning)
                    full_reasoning_parts.append(tagged_reasoning)
                    yield emit("reasoning", tagged_reasoning)
                if visible_text:
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    visible_char_count += len(visible_text)
                    full_visible_text_parts.append(visible_text)
                    yield emit("token", visible_text)

        trailing_visible, trailing_reasoning = parser.flush(
            emit_tag_reasoning=not structured_reasoning_seen
        )
        if trailing_reasoning:
            reasoning_char_count += len(trailing_reasoning)
            full_reasoning_parts.append(trailing_reasoning)
            yield emit("reasoning", trailing_reasoning)
        if trailing_visible:
            if first_token_at is None:
                first_token_at = time.perf_counter()
            visible_char_count += len(trailing_visible)
            full_visible_text_parts.append(trailing_visible)
            yield emit("token", trailing_visible)

        should_retry_direct = (
            finish_reason == "length"
            and model_attribute.upper() == "THINKING"
            and visible_char_count < 240
            and reasoning_char_count > max(visible_char_count * 2, 300)
        )

        if should_retry_direct:
            direct_retry_used = True
            yield emit("status", "Reasoning ran long. Finishing with a concise direct answer...")
            recovery_messages = prompt_messages + [
                {
                    "role": "user",
                    "content": (
                        "Your previous response spent too much token budget on reasoning and was cut off before the final answer. "
                        "Using the same contract context, provide the best final answer directly. "
                        "Do not include <think> tags, hidden reasoning, or preamble. "
                        "Start immediately with the answer and keep it concise but complete."
                    ),
                }
            ]
            recovery_response = client.chat.completions.create(
                model=model,
                messages=recovery_messages,
                stream=True,
                temperature=0.2,
                max_tokens=min(1200, max_tokens),
            )
            recovery_parser = ThinkStreamParser()
            finish_reason = "recovered_direct_answer"
            for chunk in recovery_response:
                if not chunk.choices:
                    continue
                usage = _extract_usage(chunk) or usage
                delta = chunk.choices[0].delta
                content_delta = delta.content if delta else None
                if content_delta is None:
                    continue
                visible_text, _ = recovery_parser.process(content_delta, emit_tag_reasoning=False)
                if visible_text:
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    full_visible_text_parts.append(visible_text)
                    yield emit("token", visible_text)
            trailing_visible, _ = recovery_parser.flush(emit_tag_reasoning=False)
            if trailing_visible:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                full_visible_text_parts.append(trailing_visible)
                yield emit("token", trailing_visible)

        finished_at = time.perf_counter()
        yield from _emit_model_stats(
            started_at=started_at,
            first_token_at=first_token_at,
            finished_at=finished_at,
            finish_reason=finish_reason,
            visible_text="".join(full_visible_text_parts),
            reasoning_text="".join(full_reasoning_parts),
            context_items=len(metadata),
            usage=usage,
            direct_retry_used=direct_retry_used,
        )

        yield emit("done", "")
        
    except Exception as e:
        traceback.print_exc()
        yield emit("error", str(e))
