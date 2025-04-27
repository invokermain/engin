from typing import Any

import pytest

from engin import Assembler, Provide


class A: ...


class B: ...


class C: ...


class D: ...


class E: ...


class F: ...


class G: ...


def provide_a() -> A:
    return A()


def provide_b(a: A) -> B:
    return B()


def provide_c(a: A, b: B) -> C:
    return C()


def provide_d(a: A, b: B, c: C) -> D:
    return D()


def provide_e(a: A, b: B, c: C, d: D) -> E:
    return E()


def provide_f(a: A, b: B, c: C, d: D, e: E) -> F:
    return F()


def provide_g(a: A, b: B, c: C, d: D, e: E, f: F) -> G:
    return G()


def provide_a_many() -> list[Any]:
    return [A()]


def provide_b_many(a: A) -> list[Any]:
    return [B()]


def provide_c_many(a: A, b: B) -> list[Any]:
    return [C()]


def provide_d_many(a: A, b: B, c: C) -> list[Any]:
    return [D()]


def provide_e_many(a: A, b: B, c: C, d: D) -> list[Any]:
    return [E()]


def provide_f_many(a: A, b: B, c: C, d: D, e: E) -> list[Any]:
    return [F()]


def provide_g_many(a: A, b: B, c: C, d: D, e: E, f: F) -> list[Any]:
    return [G()]


async def main() -> None:
    assembler = Assembler(
        [
            Provide(provide_a),
            Provide(provide_b),
            Provide(provide_c),
            Provide(provide_d),
            Provide(provide_e),
            Provide(provide_f),
            Provide(provide_g),
            Provide(provide_a_many),
            Provide(provide_b_many),
            Provide(provide_c_many),
            Provide(provide_d_many),
            Provide(provide_e_many),
            Provide(provide_f_many),
            Provide(provide_g_many),
        ]
    )
    await assembler.build(G)

    # reset cache
    assembler._assembled_outputs = {}

    await assembler.build(list[Any])


@pytest.mark.benchmark(min_rounds=10000, warmup="on")
def test_assembler_benchmark(aio_benchmark):
    aio_benchmark(main)
