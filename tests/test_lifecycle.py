from dataclasses import dataclass

from engin._lifecycle import LifecycleHook


@dataclass
class Tracker:
    state: int = 0

    def start(self) -> None:
        self.state = 1

    def stop(self) -> None:
        self.state = 2


async def test_lifecycle_hook():
    tracker = Tracker()

    hook = LifecycleHook(on_start=tracker.start, on_stop=tracker.stop)

    assert tracker.state == 0

    async with hook:
        assert tracker.state == 1

    assert tracker.state == 2
