"""vLLM local runner stub."""
class VLLMLocal:
    def __init__(self, model_path: str):
        self.model_path = model_path

    def start(self):
        # non-functional placeholder
        pass

    def complete(self, prompt: str) -> str:
        return "[simulated vLLM completion]"
