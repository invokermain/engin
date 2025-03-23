from dataclasses import dataclass

import pytest

from engin._lifecycle import LifecycleHook


@dataclass
class Tracker:
    state: int = 0

    def start(self) -> None:
        self.state = 1

    def stop(self) -> None:
        self.state = 2


@dataclass
class AsyncTracker:
    state: int = 0

    async def start(self) -> None:
        self.state = 1

    async def stop(self) -> None:
        self.state = 2


@pytest.mark.parametrize("tracker", (Tracker(), AsyncTracker()))
async def test_lifecycle_hook(tracker):
    tracker = Tracker()

    hook = LifecycleHook(on_start=tracker.start, on_stop=tracker.stop)

    assert tracker.state == 0

    async with hook:
        assert tracker.state == 1

    assert tracker.state == 2
