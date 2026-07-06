"""Episodic memory (in-memory sliding window placeholder)."""
from collections import deque

class EpisodicMemory:
    def __init__(self, maxlen=100):
        self.buffer = deque(maxlen=maxlen)

    def add(self, item):
        self.buffer.append(item)
