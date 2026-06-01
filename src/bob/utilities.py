import inspect
from types import FrameType


def get_caller_frame() -> FrameType:
    """
    Get the frame of the current function's caller.
    """

    current = inspect.currentframe()
    assert current is not None

    caller = current.f_back
    assert caller is not None

    callers_caller = caller.f_back
    assert callers_caller is not None

    return callers_caller
