import time
from collections import deque


class SlidingWindowLimiter:
    """Лимитер запросов в скользящем окне.

    Хранит счётчик в памяти процесса — для локального
    однопользовательского сервера этого достаточно. Важно: если
    когда-нибудь запустишь uvicorn с несколькими воркерами
    (--workers > 1), у каждого воркера будет свой счётчик, и
    реальный лимит станет max_requests * workers.
    """

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._times = deque()

    def allow(self) -> bool:
        now = time.time()
        while self._times and now - self._times[0] > self.window_seconds:
            self._times.popleft()
        if len(self._times) >= self.max_requests:
            return False
        self._times.append(now)
        return True
