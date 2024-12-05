import random
import typing
from ast import *


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


def list_wrapper(nodes: list[AST]) -> AST:
    """
    Wrap a list of nodes as an `ast.List` node
    """
    if len(nodes) == 0:
        return Constant(value=...)
    if len(nodes) == 1:
        return nodes[0]
    return List(elts=nodes, ctx=Load())


def chain_call_wrapper(nodes: list[AST]) -> AST:
    if len(nodes) == 0:
        return Constant(value=...)
    if len(nodes) == 1:
        return nodes[0]
    runner = NamedExpr(
        target=Name(id="__on_run", ctx=Store()),
        value=Lambda(
            args=arguments(
                posonlyargs=[],
                args=[arg(arg="arg")],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=Name(id="__on_run", ctx=Load()),
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


def never_call(*args, **kwargs) -> typing.NoReturn:
    raise RuntimeError("this function should never be called")  # pragma: no cover


def ast_debug_info(node: AST):
    return f"At line {node.lineno}, col {node.col_offset}: "
