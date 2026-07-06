"""LLama.cpp runner wrapper that tries to use a local llama.cpp binary when enabled.

This wrapper is intentionally conservative: by default it simulates completions.
Enable live LLM usage by setting config.security.enable_live_execution = true and
setting an appropriate model path in config/models.yaml.
"""
import subprocess
from typing import Optional

class LlamaCPPRunner:
    def __init__(self, model_path: str, live: bool = False):
        self.model_path = model_path
        self.live = live

    def generate(self, prompt: str, max_tokens: int = 128) -> str:
        if not self.live:
            return "[simulated llama.cpp response]"

        # Attempt to call a CLI binary named 'llama' (llama.cpp frontend) — this is optional
        try:
            cmd = ["llama", "-m", self.model_path, "-p", prompt, "-n", str(max_tokens)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                return "[llama failed: {}]".format(res.stderr.strip())
            return res.stdout.strip()
        except FileNotFoundError:
            return "[llama binary not found on PATH]"
        except Exception as e:
            return f"[llama error: {e}]"
