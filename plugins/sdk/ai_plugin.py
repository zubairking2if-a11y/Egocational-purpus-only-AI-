"""AI plugin contract."""
class AIPluginContract:
    def infer(self, text: str):
        raise NotImplementedError
