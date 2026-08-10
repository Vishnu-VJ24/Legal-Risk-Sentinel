_EXPORTS = {
    "Settings": (".config", "Settings"),
    "get_settings": (".config", "get_settings"),
    "extract_pdf": (".extraction", "extract_pdf"),
    "normalize_text": (".normalization", "normalize_text"),
    "SectionNode": (".sections", "SectionNode"),
    "extract_sections_from_text": (".sections", "extract_sections_from_text"),
    "fallback_chunks": (".sections", "fallback_chunks"),
    "map_sections_to_pages": (".sections", "map_sections_to_pages"),
    "build_reference_edges": (".references", "build_reference_edges"),
    "run_llm_graph_verification": (".llm_verify", "run_llm_graph_verification"),
    "aggregate_edges_raw": (".aggregation", "aggregate_edges_raw"),
    "build_adjacency": (".graph_ops", "build_adjacency"),
    "get_context_pack": (".graph_ops", "get_context_pack"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
