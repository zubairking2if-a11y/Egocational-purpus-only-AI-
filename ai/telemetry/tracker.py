"""Telemetry tracker (offline token accounting placeholder)."""
class Telemetry:
    def __init__(self):
        self.usage = {}

    def record(self, model, tokens):
        self.usage.setdefault(model, 0)
        self.usage[model] += tokens
