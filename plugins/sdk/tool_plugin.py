"""Plugin SDK: abstract contracts for third-party extensions."""
class ToolPlugin:
    def run(self, target: str):
        raise NotImplementedError

class AIPlugin:
    def complete(self, prompt: str):
        raise NotImplementedError
