"""LLM runner integration: helper to create a LlamaCPP runner based on config."""
import yaml
from ai.engine.llama_cpp import LlamaCPPRunner


def get_llama_runner():
    try:
        with open("config/models.yaml", "r") as fh:
            cfg = yaml.safe_load(fh)
    except Exception:
        cfg = {}
    model_cfg = cfg.get("models", {}).get("default", {})
    model_path = model_cfg.get("path", "/models/bge-m3.gguf")
    # live is gated behind security.enable_live_execution
    try:
        with open("config/security.yaml", "r") as fh:
            sec = yaml.safe_load(fh)
    except Exception:
        sec = {}
    live = bool(sec.get("enable_live_execution", False))
    return LlamaCPPRunner(model_path=model_path, live=live)
