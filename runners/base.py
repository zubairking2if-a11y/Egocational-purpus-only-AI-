"""Runners: secure execution interfaces and placeholders."""
class RunnerBase:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    async def run(self, target: str, args: list):
        raise NotImplementedError
