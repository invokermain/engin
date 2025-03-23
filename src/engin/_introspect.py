import inspect
from collections.abc import Iterable
from inspect import FrameInfo


def walk_stack() -> Iterable[FrameInfo]:
    """
    Fast alternative to `inspect.stack()`

    Compared to `inspect.stack()`:
     - Does not read source files to load neighboring context
     - Less accurate filename determination, still correct for most cases
     - Does not compute 3.11+ code positions (PEP 657)
    """

    frame = inspect.currentframe()

    while frame := frame and frame.f_back:
        yield inspect.FrameInfo(
            frame,
            inspect.getfile(frame),
            frame.f_lineno,
            frame.f_code.co_name,
            None,
            None,
        )


def get_first_external_frame() -> FrameInfo:
    for frame_info in walk_stack():
        frame = frame_info.frame
        if frame.f_globals["__package__"] != "engin" or frame.f_back is None:
            return frame_info
    raise RuntimeError("Unable to find external frame")
