# backend/response_cache.py
# BSCS23158 - PDC Assignment 02
# Prompt-keyed LRU cache for fallback responses

from collections import OrderedDict


class ResponseCache:
    """
    Simple LRU cache mapping prompt → last known good LLM response.
    When the circuit is open we return the most recent cached answer
    for that prompt, or a generic degraded-mode message.
    """

    DEGRADED_MSG = (
        "StudySync AI is temporarily unavailable due to a backend issue. "
        "Your request has been noted — please try again in a moment."
    )

    def __init__(self, capacity: int = 128):
        self._capacity = capacity
        self._store: OrderedDict[str, str] = OrderedDict()

    def get(self, prompt: str) -> str:
        key = prompt.strip().lower()
        if key in self._store:
            self._store.move_to_end(key)   # mark as recently used
            return self._store[key]
        return self.DEGRADED_MSG

    def put(self, prompt: str, response: str) -> None:
        key = prompt.strip().lower()
        self._store[key] = response
        self._store.move_to_end(key)
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)  # evict oldest

    def size(self) -> int:
        return len(self._store)
