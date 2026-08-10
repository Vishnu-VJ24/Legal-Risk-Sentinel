import time
from typing import Callable, List

import openai

from .config import get_settings

DEFAULT_BATCH_SIZE = 64
DEFAULT_BATCH_MAX_CHARS = 120_000

# Global state for fallback tracking
_USE_LOCAL_FALLBACK = None
_LOCAL_EMBEDDER = None


def build_embedding_batches(
    texts: List[str],
    max_items: int = DEFAULT_BATCH_SIZE,
    max_chars: int = DEFAULT_BATCH_MAX_CHARS,
) -> list[list[tuple[int, str]]]:
    """Keep retrieval records separate while packing API requests efficiently."""
    batches: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_chars = 0

    for index, text in enumerate(texts):
        if not text.strip():
            continue
        text_chars = len(text)
        exceeds_item_limit = len(current) >= max_items
        exceeds_payload_limit = current and current_chars + text_chars > max_chars
        if exceeds_item_limit or exceeds_payload_limit:
            batches.append(current)
            current = []
            current_chars = 0
        current.append((index, text))
        current_chars += text_chars

    if current:
        batches.append(current)
    return batches

def _get_local_embeddings(texts: List[str]) -> List[List[float]]:
    global _LOCAL_EMBEDDER
    if _LOCAL_EMBEDDER is None:
        model_name = get_settings().fallback_embedding_model
        print(f"🤖 [Local Embedder] Loading {model_name} into memory...")
        try:
            from sentence_transformers import SentenceTransformer
            _LOCAL_EMBEDDER = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError(
                "Local embedding fallback requires `sentence-transformers` and its runtime dependencies. "
                "Install them separately before enabling FORCE_LOCAL_EMBEDDINGS."
            )
            
    # generate embeddings and normalize
    embeddings = _LOCAL_EMBEDDER.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()

def get_embeddings(
    texts: List[str],
    api_key: str,
    input_type: str = "passage",
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> List[List[float]]:
    global _USE_LOCAL_FALLBACK
    
    # Initialize from settings on first call if not set by fallback yet
    if _USE_LOCAL_FALLBACK is None:
        _USE_LOCAL_FALLBACK = get_settings().force_local_embeddings

    if not texts:
        return []

    # If fallback is active either from .env or previous failure, route immediately
    if _USE_LOCAL_FALLBACK:
        embeddings = _get_local_embeddings(texts)
        if progress_callback:
            progress_callback(len(texts), len(texts), f"{len(texts)} / {len(texts)} items embedded")
        return embeddings

    client = openai.OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        timeout=30.0  # Added timeout to prevent indefinite hanging
    )

    all_embeddings: list[List[float]] = [[] for _ in texts]
    processed_items = 0
    total_items = len([t for t in texts if t.strip()]) or len(texts)
    runtime_settings = get_settings()
    batches = build_embedding_batches(
        texts,
        max_items=runtime_settings.embedding_batch_size,
        max_chars=runtime_settings.embedding_batch_max_chars,
    )
    
    # Process in batches to respect typical API limits
    for indexed_batch in batches:
        indexes, batch = zip(*indexed_batch)
        batch = list(batch)
            
        max_retries = 3
        fall_back = False
        
        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    input=batch,
                    model=get_settings().embedding_model,
                    encoding_format="float",
                    extra_body={"input_type": input_type, "truncate": "END"}
                )
                
                if len(response.data) != len(batch):
                    raise ValueError(
                        f"Embedding response count mismatch: expected {len(batch)}, got {len(response.data)}"
                    )
                for index, data in zip(indexes, response.data):
                    all_embeddings[index] = data.embedding
                processed_items += len(batch)
                if progress_callback:
                    progress_callback(
                        processed_items,
                        total_items,
                        f"{processed_items} / {total_items} items embedded",
                    )
                    
                break # success
                
            except openai.APITimeoutError as e:
                # Immediate fallback on timeout
                print(f"⚠️ Embedding API timed out: {e}")
                fall_back = True
                break
            except Exception as e:
                print(f"⚠️ Embedding API failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    fall_back = True
                else:
                    time.sleep(2) # brief pause before retry
                    
        if fall_back:
            local_model = get_settings().fallback_embedding_model
            print(f"  ↳ Enabling global local fallback ({local_model}) for all subsequent embedding tasks.")
            _USE_LOCAL_FALLBACK = True
            
            # Since NVIDIA failed mid-way, and dimensionality must match across this entire list of texts,
            # we abandon the NVIDIA results and process all provided texts through the local model.
            embeddings = _get_local_embeddings(texts)
            if progress_callback:
                progress_callback(len(texts), len(texts), f"{len(texts)} / {len(texts)} items embedded")
            return embeddings
            
    return all_embeddings
