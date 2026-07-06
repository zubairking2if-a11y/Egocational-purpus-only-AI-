"""Vector store shim for LanceDB/Chroma-like API (placeholder)."""
class VectorStore:
    def __init__(self, path: str):
        self.path = path

    def add(self, doc_id, vector):
        pass
