import typing
import itertools
import enum
from ast import *

__all__ = [
    "Scope",
    "ScopeGlobal",
    "ScopeFunction",
    "ScopeClass",
    "analyze_scopes",
]

_CompTypes: typing.TypeAlias = ListComp | SetComp | DictComp | GeneratorExp


class SymbolTypeFlags(enum.Enum):
    LOCAL = 0
    FREE = enum.auto()
    GLOBAL = enum.auto()
    NONLOCAL_SRC = enum.auto()
    NONLOCAL_DST = enum.auto()
    PARAMETER = enum.auto()


T = typing.TypeVar("T", Module, FunctionDef, ClassDef)


class Scope(typing.Generic[T]):
    node: T
    inner_scopes: list["Scope"]
    global_scope: "ScopeGlobal"

    symbols: dict[str, SymbolTypeFlags]

    def __init__(self, node: T, globol_scope: "ScopeGlobal") -> None:
        self.node = node
        self.global_scope = globol_scope
        self.inner_scopes = []
        self.symbols = {}

        stack: list[stmt] = list(reversed(node.body))
        while stack:
            top = stack.pop()
            self._analize_stmt(top)
            stack.extend(self._unfold_stmt(top))

    def _unfold_stmt(self, node: stmt) -> typing.Iterable[stmt]:
        if isinstance(node, (If, While, For)):
            return itertools.chain(reversed(node.body), reversed(node.orelse))
        return []

    def _analize_stmt(self, node: stmt) -> None:
        if isinstance(node, FunctionDef):
            self._declare_symbol(node.name)
            for default in node.args.defaults:
                self._analize_expr(default)
            for kw_default in node.args.kw_defaults:
                if kw_default is not None:
                    self._analize_expr(kw_default)
            self.inner_scopes.append(ScopeFunction(node, self, self.global_scope))
        elif isinstance(node, ClassDef):
            self._declare_symbol(node.name)
            for base in node.bases:
                self._analize_expr(base)
            for kw in node.keywords:
                self._analize_expr(kw.value)
            self.inner_scopes.append(ScopeClass(node, self, self.global_scope))
        elif isinstance(node, Expr):
            self._analize_expr(node.value)
        elif isinstance(node, (If, While)):
            self._analize_expr(node.test)
        elif isinstance(node, For):
            self._analize_expr(node.iter)
        elif isinstance(node, (Break, Continue, Pass)):
            pass
        elif isinstance(node, Return) and node.value is not None:
            self._analize_expr(node.value)
        elif isinstance(node, (AugAssign, AnnAssign)) and node.value is not None:
            self._analize_expr(node.target)
            self._analize_expr(node.value)
        elif isinstance(node, Assign):
            self._analize_expr(node.value)
            for target in node.targets:
                self._analize_expr(target)
        elif isinstance(node, Global):
            for name in node.names:
                self._bind_global(name)
        elif isinstance(node, Nonlocal):
            for name in node.names:
                self._bind_nonlocal(name)
        elif isinstance(node, Import):
            pass  # todo
        elif isinstance(node, ImportFrom):
            pass  # todo

    def _analize_expr(self, node: expr) -> None:
        stack: list[expr] = [node]

        def handle_generic_expr(_node: expr):
            for field_name in _node._fields:
                if not hasattr(_node, field_name):
                    continue
                field = getattr(_node, field_name)
                if isinstance(field, expr):
                    stack.append(field)
                elif isinstance(field, list):
                    stack.extend(reversed(field))

        while stack:
            top = stack.pop()
            if isinstance(top, Name):
                if isinstance(top.ctx, Load):
                    self._reference_symbol(top.id)
                elif isinstance(top.ctx, Store):
                    self._declare_symbol(top.id)
            elif isinstance(top, NamedExpr):
                self._declare_symbol(top.target.id)
                stack.append(top.value)
            elif isinstance(top, Lambda):
                pass  # todo
            elif isinstance(top, _CompTypes):
                pass  # todo
            else:
                handle_generic_expr(top)

    def _declare_symbol(self, name: str) -> None:
        raise NotImplementedError()

    def _reference_symbol(self, name: str) -> None:
        raise NotImplementedError()

    def _bind_global(self, name: str) -> None:
        raise NotImplementedError()

    def _bind_nonlocal(self, name: str) -> None:
        raise NotImplementedError()


class ScopeGlobal(Scope[Module]):
    def __init__(self, node: Module) -> None:
        self.global_scope = self
        super().__init__(node, self)

    def _declare_symbol(self, name: str):
        self.symbols[name] = SymbolTypeFlags.LOCAL

    def _reference_symbol(self, name: str) -> None:
        pass

    def _bind_global(self, name: str) -> None:
        pass

    def _bind_nonlocal(self, name: str) -> None:
        raise SyntaxError("nonlocal declaration not allowed at module level")


class ScopeFunction(Scope[FunctionDef]):
    outer_scope: Scope

    nonlocal_reference_dict: dict[str, "ScopeFunction"]

    def __init__(
        self, node: FunctionDef, outer_scope: Scope, global_scope: ScopeGlobal
    ) -> None:
        self.outer_scope = outer_scope
        super().__init__(node, global_scope)


class ScopeClass(Scope[ClassDef]):
    outer_scope: Scope

    global_symbol_list: list[str]
    nonlocal_symbol_dict: dict[str, ScopeFunction]

    def __init__(
        self, node: ClassDef, outer_scope: Scope, global_scope: ScopeGlobal
    ) -> None:
        self.outer_scope = outer_scope
        super().__init__(node, global_scope)


def analyze_scopes(root_node: Module) -> ScopeGlobal:
    return ScopeGlobal(root_node)
