import random
import typing
from ast import *

from oneliner.config import Configs
from oneliner.reserved_identifiers import OL_RUN


def unique_id() -> str:
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))


def convert_slice(_slice: Slice) -> Call:
    """
    Convert slice expt to a call of slice function
    to prevent invalid syntax like `__setitem__(0:10:2, value)`
    """
    _slice_value = lambda v: Constant(None) if v is None else v
    return Call(
        func=Name(id="slice", ctx=Load()),
        args=[
            _slice_value(_slice.lower),
            _slice_value(_slice.upper),
            _slice_value(_slice.step),
        ],
        keywords=[],
    )


def list_wrapper(nodes: list[expr]) -> expr:
    return List(elts=nodes, ctx=Load())


def chain_call_wrapper(nodes: list[expr]) -> expr:
    runner = NamedExpr(
        target=Name(id=OL_RUN, ctx=Store()),
        value=Lambda(
            args=arguments(
                posonlyargs=[],
                args=[arg(arg="_")],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=Name(id=OL_RUN, ctx=Load()),
        ),
    )
    call = Call(
        func=runner,
        args=[nodes[0]],
        keywords=[],
    )
    for node in nodes[1:]:
        call = Call(func=call, args=[], keywords=[])
        call.args.append(node)

    return call


def get_expr_wrapper(configs: Configs):
    if configs.expr_wrapper == "chain_call":
        _wrapper_internal = chain_call_wrapper
    else:
        _wrapper_internal = list_wrapper

    def wraper(nodes: list[expr]) -> expr:
        """Wrap a list of expr nodes as one expr"""
        if len(nodes) == 0:
            return Constant(value=...)
        if len(nodes) == 1:
            return nodes[0]

        return _wrapper_internal(nodes)

    return wraper


def never_call(*args, **kwargs) -> typing.NoReturn:
    raise RuntimeError("this function should never be called")  # pragma: no cover


def ast_debug_info(node: stmt | expr):
    return f"At line {node.lineno}, col {node.col_offset}: "
