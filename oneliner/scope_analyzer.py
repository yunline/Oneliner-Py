from ast import Module
import typing
import itertools
import enum
from ast import *

__all__ = [
    "SymbolTypeFlags",
    "ScopeAnalysisError",
    "Scope",
    "ScopeGlobal",
    "ScopeFunction",
    "ScopeLambda",
    "ScopeComprehensions",
    "ScopeClass",
    "analyze_scopes",
]


class SymbolTypeFlags(enum.Flag):
    REFERENCED_GLOBAL = 1
    LOCAL = enum.auto()
    GLOBAL = enum.auto()
    NONLOCAL_SRC = enum.auto()
    NONLOCAL_DST = enum.auto()
    FREE = enum.auto()
    PARAMETER = enum.auto()
    COMPREHENSION_TARGET = enum.auto()
    COMPREHENSION_REFERENCE = enum.auto()
    COMPREHENSION_ASSIGNMENT = enum.auto()


class ScopeAnalysisError(RuntimeError):
    pass


# comp types (used by type alias)
Comprehensions: typing.TypeAlias = ListComp | SetComp | DictComp | GeneratorExp

# comp types (used by isinstance)
ComprehensionTypes = (ListComp, SetComp, DictComp, GeneratorExp)

T = typing.TypeVar("T", Module, FunctionDef, ClassDef, Lambda, Comprehensions)


class Scope(typing.Generic[T]):
    node: T
    inner_scopes: list["Scope"]
    symbols: dict[str, SymbolTypeFlags]


class ScopeGlobal(Scope[Module]):
    pass


class ScopeFunction(Scope[FunctionDef]):
    outer_scope: Scope
    nonlocal_reference_dict: dict[str, Scope]


class ScopeLambda(Scope[Lambda]):
    outer_scope: Scope
    nonlocal_reference_dict: dict[str, Scope]


class ScopeComprehensions(Scope[Comprehensions]):
    outer_scope: Scope
    comprehension_reference_dict: dict[str, Scope]


class ScopeClass(Scope[ClassDef]):
    outer_scope: Scope
    nonlocal_reference_dict: dict[str, Scope]


def get_ast_node_location_info(node: stmt | expr):
    return (
        None,  # filename, leave it None
        node.lineno,
        node.col_offset,
        None,  # text, leave it None
        node.end_lineno,
        node.end_col_offset,
    )


SymbolHandler: typing.TypeAlias = typing.Callable[
    ["AnalysisContext", str, stmt | expr], None
]


class AnalysisContext:
    node: Module | FunctionDef | ClassDef | Lambda | Comprehensions
    inner_scope_nodes: list[FunctionDef | ClassDef | Lambda | Comprehensions]
    outer_ctx: "AnalysisContext"
    inner_ctx: list["AnalysisContext"]
    symbols: dict[str, SymbolTypeFlags]
    nonlocal_reference_dict: dict[str, "AnalysisContext"]
    comprehension_reference_dict: dict[str, "AnalysisContext"]

    _assign_symbol: SymbolHandler
    _reference_symbol: SymbolHandler
    _bind_global: SymbolHandler
    _bind_nonlocal: SymbolHandler

    result: Scope

    def __init__(
        self,
        node: Module | FunctionDef | ClassDef | Lambda | Comprehensions,
        outer_ctx: "AnalysisContext|None" = None,
    ) -> None:
        self.node = node
        self.inner_scope_nodes = []
        if outer_ctx is not None:
            self.outer_ctx = outer_ctx
        self.inner_ctx = []
        self.symbols = {}

    def assign_symbol(self, name: str, node: stmt | expr) -> None:
        self._assign_symbol(self, name, node)

    def reference_symbol(self, name: str, node: stmt | expr) -> None:
        self._reference_symbol(self, name, node)

    def bind_global(self, name: str, node: stmt | expr) -> None:
        self._bind_global(self, name, node)

    def bind_nonlocal(self, name: str, node: stmt | expr) -> None:
        self._bind_nonlocal(self, name, node)


def generate_result_scope(ctx: AnalysisContext) -> None:
    ctx.result.node = ctx.node
    ctx.result.symbols = ctx.symbols
    ctx.result.inner_scopes = [inner.result for inner in ctx.inner_ctx]

    if isinstance(ctx.result, (ScopeFunction, ScopeClass, ScopeLambda)):
        ctx.result.outer_scope = ctx.outer_ctx.result
        ctx.result.nonlocal_reference_dict = {}
        for name, referenced_ctx in ctx.nonlocal_reference_dict.items():
            ctx.result.nonlocal_reference_dict[name] = referenced_ctx.result

            # set NONLOCAL_SRC flags
            if isinstance(ctx.result, (ScopeFunction, ScopeLambda)):
                referenced_ctx.symbols[name] |= SymbolTypeFlags.NONLOCAL_SRC

            elif isinstance(ctx.result, (ScopeClass)):
                if ctx.symbols[name] == SymbolTypeFlags.NONLOCAL_DST:
                    referenced_ctx.symbols[name] |= SymbolTypeFlags.NONLOCAL_SRC

    if isinstance(ctx.result, ScopeComprehensions):
        ctx.result.outer_scope = ctx.outer_ctx.result
        ctx.result.comprehension_reference_dict = {
            k: v.result for k, v in ctx.comprehension_reference_dict.items()
        }


def register_function_args(ctx: AnalysisContext, args: arguments):
    for arg in itertools.chain(args.posonlyargs, args.args, args.kwonlyargs):
        ctx.symbols[arg.arg] = SymbolTypeFlags.PARAMETER
    if args.vararg is not None:
        ctx.symbols[args.vararg.arg] = SymbolTypeFlags.PARAMETER
    if args.kwarg is not None:
        ctx.symbols[args.kwarg.arg] = SymbolTypeFlags.PARAMETER


def assign_symbol_global(ctx: AnalysisContext, name: str, node: stmt | expr):
    ctx.symbols[name] = SymbolTypeFlags.GLOBAL


def assign_symbol_local(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    if name in ctx.symbols:
        if ctx.symbols[name] == SymbolTypeFlags.REFERENCED_GLOBAL:
            pass
        elif ctx.symbols[name] == SymbolTypeFlags.FREE:
            del ctx.nonlocal_reference_dict[name]
        else:
            return

    ctx.symbols[name] = SymbolTypeFlags.LOCAL


def assign_symbol_comprehensions_target(
    ctx: AnalysisContext, name: str, node: stmt | expr
) -> None:
    ctx.symbols[name] = SymbolTypeFlags.COMPREHENSION_TARGET


def assign_symbol_comprehensions(
    ctx: AnalysisContext, name: str, node: stmt | expr
) -> None:
    outer = ctx
    while isinstance(outer.node, ComprehensionTypes):
        if (
            name in outer.symbols
            and outer.symbols[name] & SymbolTypeFlags.COMPREHENSION_TARGET
        ):
            raise SyntaxError(
                f"assignment expression cannot rebind comprehension iteration variable '{name}'",
                get_ast_node_location_info(node),
            )
        outer = outer.outer_ctx

    ctx.comprehension_reference_dict[name] = outer

    if isinstance(outer.node, Module):
        ctx.symbols[name] = SymbolTypeFlags.COMPREHENSION_ASSIGNMENT
        return

    if isinstance(outer.node, (FunctionDef, Lambda)):
        ctx.symbols[name] = SymbolTypeFlags.COMPREHENSION_ASSIGNMENT
        if name in outer.symbols:
            if outer.symbols[name] == SymbolTypeFlags.REFERENCED_GLOBAL:
                outer.symbols[name] = SymbolTypeFlags.LOCAL
        else:
            outer.symbols[name] = SymbolTypeFlags.LOCAL
        return

    if isinstance(outer.node, ClassDef):
        raise SyntaxError(
            "assignment expression within a comprehension cannot be used in a class body",
            get_ast_node_location_info(node),
        )

    raise ScopeAnalysisError(  # pragma: no cover
        f"Invalid outer scope '{type(outer.node)}' was found "
        f"when analyzing assignment in comprehension"
    )


def reference_symbol_global(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    if name not in ctx.symbols:
        ctx.symbols[name] = SymbolTypeFlags.REFERENCED_GLOBAL


def reference_symbol_local(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    if name in ctx.symbols:
        return

    outer = ctx.outer_ctx
    while True:
        if isinstance(outer.node, Lambda) and not isinstance(ctx.node, Lambda):
            raise ScopeAnalysisError(  # pragma: no cover
                f"Scope '{type(ctx.node)}' shall never be inside of a Lambda scope"
            )

        if isinstance(outer.node, Module):
            ctx.symbols[name] = SymbolTypeFlags.REFERENCED_GLOBAL
            break

        if isinstance(outer.node, ClassDef):
            outer = outer.outer_ctx
            continue

        if isinstance(outer.node, (FunctionDef, Lambda)):
            if name in outer.symbols:
                if not outer.symbols[name] & (
                    SymbolTypeFlags.REFERENCED_GLOBAL | SymbolTypeFlags.FREE
                ):
                    ctx.symbols[name] = SymbolTypeFlags.FREE
                    ctx.nonlocal_reference_dict[name] = outer
                    break
            outer = outer.outer_ctx
            continue

        raise ScopeAnalysisError(  # pragma: no cover
            f"Invalid outer scope '{type(outer.node)}' was found "
            f"when analyzing reference in local scope"
        )


def reference_symbol_comprehensions(
    ctx: AnalysisContext, name: str, node: stmt | expr
) -> None:
    if name in ctx.symbols:
        return

    ctx.symbols[name] = SymbolTypeFlags.COMPREHENSION_REFERENCE
    outer = ctx.outer_ctx
    while isinstance(outer.node, ComprehensionTypes):
        if name in outer.symbols:
            if outer.symbols[name] & SymbolTypeFlags.COMPREHENSION_TARGET:
                break
        outer = outer.outer_ctx
    ctx.comprehension_reference_dict[name] = outer


def bind_global_global(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    pass


def bind_global_local(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    if name not in ctx.symbols:
        ctx.symbols[name] = SymbolTypeFlags.GLOBAL
        return
    sym = ctx.symbols[name]
    if sym & SymbolTypeFlags.GLOBAL:
        return
    if sym & SymbolTypeFlags.LOCAL:
        raise SyntaxError(
            f"name '{name}' is assigned to before global declaration",
            get_ast_node_location_info(node),
        )
    if sym & (SymbolTypeFlags.REFERENCED_GLOBAL | SymbolTypeFlags.FREE):
        raise SyntaxError(
            f"name '{name}' is used prior to global declaration",
            get_ast_node_location_info(node),
        )
    if sym & SymbolTypeFlags.PARAMETER:
        raise SyntaxError(
            f"name '{name}' is parameter and global",
            get_ast_node_location_info(node),
        )
    if sym & SymbolTypeFlags.NONLOCAL_DST:
        raise SyntaxError(
            f"name '{name}' is nonlocal and global",
            get_ast_node_location_info(node),
        )

    raise ScopeAnalysisError(  # pragma: no cover
        f"Unable to declare symbol '{name}' global. "
        f"The flags of the symbol are: {ctx.symbols[name]}"
    )


def bind_nonlocal_global(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    raise SyntaxError(
        "nonlocal declaration not allowed at module level",
        get_ast_node_location_info(node),
    )


def bind_nonlocal_local(ctx: AnalysisContext, name: str, node: stmt | expr) -> None:
    if name in ctx.symbols:
        sym = ctx.symbols[name]
        if sym & SymbolTypeFlags.NONLOCAL_DST:
            return
        if sym & SymbolTypeFlags.GLOBAL:
            raise SyntaxError(
                f"name '{name}' is nonlocal and global",
                get_ast_node_location_info(node),
            )
        if sym & SymbolTypeFlags.LOCAL:
            raise SyntaxError(
                f"name '{name}' is assigned prior to nonlocal declaration",
                get_ast_node_location_info(node),
            )
        if sym & SymbolTypeFlags.PARAMETER:
            raise SyntaxError(
                f"name '{name}' is parameter and nonlocal",
                get_ast_node_location_info(node),
            )
        if sym & (SymbolTypeFlags.REFERENCED_GLOBAL | SymbolTypeFlags.FREE):
            raise SyntaxError(
                f"name '{name}' is used to before nonlocal declaration",
                get_ast_node_location_info(node),
            )

        raise ScopeAnalysisError(  # pragma: no cover
            f"Unable to declare symbol '{name}' nonlocal. "
            f"The flags of the symbol are: {ctx.symbols[name]}"
        )

    outer = ctx.outer_ctx
    while True:
        if isinstance(outer.node, Module):
            raise SyntaxError(f"no binding for nonlocal '{name}' found")

        if isinstance(outer.node, ClassDef):
            outer = outer.outer_ctx
            continue

        if isinstance(outer.node, FunctionDef):
            if name in outer.symbols:
                ctx.symbols[name] = SymbolTypeFlags.NONLOCAL_DST
                ctx.nonlocal_reference_dict[name] = outer
                break
            outer = outer.outer_ctx
            continue

        raise ScopeAnalysisError(  # pragma: no cover
            f"Invalid outer scope '{type(outer.node)}' was found "
            f"when searching source of nonlocal"
        )


def analyze_block(ctx: AnalysisContext, node: Module | FunctionDef | ClassDef) -> None:
    stack: list[stmt] = list(reversed(node.body))

    while stack:
        top = stack.pop()
        if isinstance(top, FunctionDef):
            ctx.inner_scope_nodes.append(top)
            ctx.assign_symbol(top.name, top)
            for deco in top.decorator_list:
                analyze_expr(ctx, deco)
            for default in top.args.defaults:
                analyze_expr(ctx, default)
            for kw_default in top.args.kw_defaults:
                if kw_default is not None:
                    analyze_expr(ctx, kw_default)
        elif isinstance(top, ClassDef):
            ctx.inner_scope_nodes.append(top)
            ctx.assign_symbol(top.name, top)
            for deco in top.decorator_list:
                analyze_expr(ctx, deco)
            for base in top.bases:
                analyze_expr(ctx, base)
            for kw in top.keywords:
                analyze_expr(ctx, kw.value)
        elif isinstance(top, Expr):
            analyze_expr(ctx, top.value)
        elif isinstance(top, (If, While)):
            analyze_expr(ctx, top.test)
            stack.extend(reversed(top.body))
            stack.extend(reversed(top.orelse))
        elif isinstance(top, For):
            analyze_expr(ctx, top.target)
            analyze_expr(ctx, top.iter)
            stack.extend(reversed(top.body))
            stack.extend(reversed(top.orelse))
        elif isinstance(top, (Break, Continue, Pass)):
            pass
        elif isinstance(top, Return):
            if top.value is not None:
                analyze_expr(ctx, top.value)
        elif isinstance(top, (AugAssign, AnnAssign)) and top.value is not None:
            analyze_expr(ctx, top.target)
            analyze_expr(ctx, top.value)
        elif isinstance(top, Assign):
            analyze_expr(ctx, top.value)
            for target in top.targets:
                analyze_expr(ctx, target)
        elif isinstance(top, Global):
            for name in top.names:
                ctx.bind_global(name, top)
        elif isinstance(top, Nonlocal):
            for name in top.names:
                ctx.bind_nonlocal(name, top)
        elif isinstance(top, (Import, ImportFrom)):
            for alias in top.names:
                if alias.asname:
                    ctx.assign_symbol(alias.asname, top)
                else:
                    ctx.assign_symbol(alias.name, top)
        else:
            raise ScopeAnalysisError(f"Unsupported statement type '{type(top)}'")


def analyze_expr(ctx: AnalysisContext, node: expr) -> None:
    stack: list[expr] = [node]

    while stack:
        top = stack.pop()
        if isinstance(top, Name):
            if isinstance(top.ctx, Load):
                ctx.reference_symbol(top.id, top)
            elif isinstance(top.ctx, Store):
                ctx.assign_symbol(top.id, top)
            elif isinstance(top.ctx, Del):  # pragma: no cover
                pass
            else:  # pragma: no cover
                raise ScopeAnalysisError("Invalid expr_context of the Name node")
        elif isinstance(top, NamedExpr):
            ctx.assign_symbol(top.target.id, top)
            stack.append(top.value)
        elif isinstance(top, Lambda):
            stack.extend(top.args.defaults)
            for kw_default in top.args.kw_defaults:
                if kw_default is not None:
                    stack.append(kw_default)
            ctx.inner_scope_nodes.append(top)
        elif isinstance(top, ComprehensionTypes):
            ctx.inner_scope_nodes.append(top)
        else:
            # generic handler for any expr type
            for field_name in top._fields:
                field = getattr(top, field_name, None)
                if isinstance(field, list):
                    for _node in reversed(field):
                        # Inner node type might not always be expr.
                        # However, inner node might contain expr nodes.
                        # So let's cast them and treat them as expr.
                        if isinstance(_node, AST):
                            stack.append(typing.cast(expr, _node))
                elif isinstance(field, AST):
                    stack.append(typing.cast(expr, field))


def analyze_scopes(root_node: Module) -> ScopeGlobal:
    root_ctx = AnalysisContext(root_node)
    ctx_stack = [root_ctx]
    while ctx_stack:
        top_ctx = ctx_stack.pop()
        top_node = top_ctx.node

        # init necessary dicts
        if isinstance(top_node, (FunctionDef, ClassDef, Lambda)):
            top_ctx.nonlocal_reference_dict = {}
        elif isinstance(top_node, ComprehensionTypes):
            top_ctx.comprehension_reference_dict = {}

        # analyze
        if isinstance(top_node, Module):
            top_ctx.result = ScopeGlobal()
            top_ctx._assign_symbol = assign_symbol_global
            top_ctx._reference_symbol = reference_symbol_global
            top_ctx._bind_global = bind_global_global
            top_ctx._bind_nonlocal = bind_nonlocal_global
            analyze_block(top_ctx, top_node)

        elif isinstance(top_node, FunctionDef):
            top_ctx.result = ScopeFunction()
            top_ctx._assign_symbol = assign_symbol_local
            top_ctx._reference_symbol = reference_symbol_local
            top_ctx._bind_global = bind_global_local
            top_ctx._bind_nonlocal = bind_nonlocal_local
            register_function_args(top_ctx, top_node.args)
            analyze_block(top_ctx, top_node)

        elif isinstance(top_node, ClassDef):
            top_ctx.result = ScopeClass()
            top_ctx._assign_symbol = assign_symbol_local
            top_ctx._reference_symbol = reference_symbol_local
            top_ctx._bind_global = bind_global_local
            top_ctx._bind_nonlocal = bind_nonlocal_local
            analyze_block(top_ctx, top_node)

        elif isinstance(top_node, Lambda):
            top_ctx.result = ScopeLambda()
            top_ctx._assign_symbol = assign_symbol_local
            top_ctx._reference_symbol = reference_symbol_local
            register_function_args(top_ctx, top_node.args)
            analyze_expr(top_ctx, top_node.body)

        elif isinstance(top_node, ComprehensionTypes):
            top_ctx.result = ScopeComprehensions()

            top_ctx._assign_symbol = assign_symbol_comprehensions_target
            for gen in top_node.generators:
                analyze_expr(top_ctx, gen.target)

            top_ctx._assign_symbol = assign_symbol_comprehensions
            top_ctx._reference_symbol = reference_symbol_comprehensions
            for gen in top_node.generators:
                analyze_expr(top_ctx, gen.iter)
                for _if in gen.ifs:
                    analyze_expr(top_ctx, _if)
            if isinstance(top_node, DictComp):
                analyze_expr(top_ctx, top_node.key)
                analyze_expr(top_ctx, top_node.value)
            else:
                analyze_expr(top_ctx, top_node.elt)

        else:  # pragma: no cover
            raise ScopeAnalysisError(
                f"Invalid scope node type '{type(top_node)}' "
                f"Module, FunctionDef, ClassDef, Lambda, ListComp, "
                f"SetComp, DictComp or GeneratorExp is expected"
            )

        for node in top_ctx.inner_scope_nodes:
            inner = AnalysisContext(node, outer_ctx=top_ctx)
            top_ctx.inner_ctx.append(inner)
            ctx_stack.append(inner)

    ctx_stack = [root_ctx]
    while ctx_stack:
        top_ctx = ctx_stack.pop()
        generate_result_scope(top_ctx)
        ctx_stack.extend(top_ctx.inner_ctx)

    assert isinstance(root_ctx.result, ScopeGlobal)
    return root_ctx.result
