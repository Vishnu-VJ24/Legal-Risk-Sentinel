"""
Dynamic scaling for LLM pipeline parameters.

Computes batch sizes and max_tokens based on the actual number of clauses/sections
in the document being processed. The goal is:
  - Smaller documents → smaller batches, generous per-item token budgets
  - Larger documents → larger batches (for throughput), scaled token budgets

All functions return concrete values; no config mutation.
"""

from __future__ import annotations

import math


def compute_edge_verify_params(num_sections: int) -> dict:
    """
    Compute batch_size and max_tokens for the LLM edge verification stage.
    
    Principles:
      - Small docs (≤15): batch_size=3, generous tokens per item
      - Medium docs (16-40): batch_size=5-6, moderate tokens  
      - Large docs (41-80): batch_size=8, scaled tokens
      - Very large docs (80+): batch_size=10, larger tokens
    
    Returns:
        dict with 'batch_size', 'max_tokens', 'max_text_chars'
    """
    if num_sections <= 25:
        batch_size = 4
        max_tokens = 2000
        max_text_chars = 5000
    elif num_sections <= 60:
        batch_size = 10
        max_tokens = 2500
        max_text_chars = 4500
    elif num_sections <= 90:
        batch_size = 15
        max_tokens = 3500
        max_text_chars = 4000
    else:
        batch_size = 25
        max_tokens = 4500
        max_text_chars = 3500

    return {
        "batch_size": batch_size,
        "max_tokens": max_tokens,
        "max_text_chars": max_text_chars,
    }


def compute_risk_analyzer_params(num_sections: int) -> dict:
    """
    Compute max_tokens and batch_size for the risk analyzer stage.
    
    Risk analysis is now batched to 3 sections per prompt. We scale output tokens 
    generously because the LLM returns 3 full risk objects.
    
    Returns:
        dict with 'max_tokens' and 'batch_size'
    """
    if num_sections <= 15:
        max_tokens = 3500
    elif num_sections <= 40:
        max_tokens = 4500
    elif num_sections <= 80:
        max_tokens = 6000
    else:
        max_tokens = 8000

    return {
        "max_tokens": max_tokens,
        "batch_size": 3,
    }


def compute_report_params(num_risk_sections: int) -> dict:
    """
    Compute max_tokens for the final report generation stage.
    
    The report is an executive synthesis, not a second clause-by-clause analysis.
    Detailed findings remain available in the ledger and risk review UI.
    
    Returns:
        dict with 'max_tokens'
    """
    base_tokens = 2048
    per_section_tokens = 128
    computed = base_tokens + (num_risk_sections * per_section_tokens)
    max_tokens = max(2048, min(4096, computed))
    max_tokens = math.ceil(max_tokens / 1024) * 1024

    return {
        "max_tokens": max_tokens,
    }


def log_scaling_decision(stage: str, num_items: int, params: dict) -> None:
    """Print a concise log line showing the scaling decision."""
    parts = [f"{k}={v}" for k, v in params.items()]
    print(f"  📐 Dynamic scaling [{stage}]: {num_items} items → {', '.join(parts)}")
