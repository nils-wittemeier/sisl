from typing import Tuple, TypeVar, Union

T1 = TypeVar("T1")
T2 = TypeVar("T2")


def swap(val: Union[T1, T2], vals: Tuple[T1, T2]) -> Union[T1, T2]:
    """Given two values, returns the one that is not the input value."""
    if val == vals[0]:
        return vals[1]
    elif val == vals[1]:
        return vals[0]
    else:
        raise ValueError(f"Value {val} not in {vals}")
