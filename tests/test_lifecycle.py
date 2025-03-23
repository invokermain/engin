from dataclasses import dataclass

import pytest

from engin._lifecycle import Lifecycle, LifecycleHook


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


@pytest.mark.parametrize("tracker", [(Tracker(), AsyncTracker())])
async def test_lifecycle_hook(tracker):
    tracker = Tracker()

    hook = LifecycleHook(on_start=tracker.start, on_stop=tracker.stop)

    async with hook:
        assert tracker.state == 1

    assert tracker.state == 2


@pytest.mark.parametrize("tracker", [(Tracker(), AsyncTracker())])
async def test_lifecycle_hook_start_only(tracker):
    tracker = Tracker()

    hook = LifecycleHook(on_start=tracker.start)

    async with hook:
        assert tracker.state == 1

    assert tracker.state == 1


@pytest.mark.parametrize("tracker", [(Tracker(), AsyncTracker())])
async def test_lifecycle_hook_stop_only(tracker):
    tracker = Tracker()

    hook = LifecycleHook(on_stop=tracker.stop)

    async with hook:
        assert tracker.state == 0

    assert tracker.state == 2


@pytest.mark.parametrize("tracker", [(Tracker(), AsyncTracker())])
async def test_lifecycle_hook_via_lifecycle(tracker):
    lifecycle = Lifecycle()
    tracker = Tracker()

    lifecycle.hook(on_start=tracker.start, on_stop=tracker.stop)
    cm = lifecycle.list()[0]

    async with cm:
        assert tracker.state == 1

    assert tracker.state == 2


def test_lifecycle_hook_invalid():
    with pytest.raises(ValueError, match="on_start"):
        Lifecycle().hook()
