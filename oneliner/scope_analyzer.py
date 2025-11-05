import typing
import itertools
import enum
from ast import *

__all__ = [
    "SymbolTypeFlags",
    "Scope",
    "ScopeGlobal",
    "ScopeFunction",
    "ScopeClass",
    "analyze_scopes",
]

_CompTypes = (ListComp, SetComp, DictComp, GeneratorExp)


class SymbolTypeFlags(enum.Flag):
    REFERENCED_GLOBAL = 1
    LOCAL = enum.auto()
    GLOBAL = enum.auto()
    NONLOCAL_SRC = enum.auto()
    NONLOCAL_DST = enum.auto()
    FREE = enum.auto()
    PARAMETER = enum.auto()


T = typing.TypeVar("T", Module, FunctionDef, ClassDef, Lambda)


class Scope(typing.Generic[T]):
    node: T
    inner_scopes: list["Scope"]
    global_scope: "ScopeGlobal"

    symbols: dict[str, SymbolTypeFlags]

    _tmp_inner_scope_nodes: list[ClassDef | FunctionDef | Lambda]

    def __init__(self, node: T, globol_scope: "ScopeGlobal") -> None:
        self.node = node
        self.global_scope = globol_scope
        self.inner_scopes = []
        self.symbols = {}
        self._tmp_inner_scope_nodes = []

    def _analyze_scope(self) -> None:
        # this method is for (Module, FunctionDef, ClassDef) only
        assert isinstance(self.node, (Module, FunctionDef, ClassDef))

        stack: list[stmt] = list(reversed(self.node.body))

        while stack:
            top = stack.pop()
            if isinstance(top, (FunctionDef, ClassDef)):
                self._tmp_inner_scope_nodes.append(top)
            self._analize_stmt(top)
            stack.extend(self._unfold_stmt(top))

        for inner_node in self._tmp_inner_scope_nodes:
            new_scope: Scope
            if isinstance(inner_node, FunctionDef):
                new_scope = ScopeFunction(inner_node, self, self.global_scope)
            elif isinstance(inner_node, ClassDef):
                new_scope = ScopeClass(inner_node, self, self.global_scope)
            else:
                new_scope = ScopeLambda(inner_node, self, self.global_scope)
            self.inner_scopes.append(new_scope)

    def _unfold_stmt(self, node: stmt) -> typing.Iterable[stmt]:
        if isinstance(node, (If, While, For)):
            return itertools.chain(reversed(node.body), reversed(node.orelse))
        return []

    def _analize_stmt(self, node: stmt) -> None:
        if isinstance(node, FunctionDef):
            self._assign_symbol(node.name)
            for deco in node.decorator_list:
                self._analize_expr(deco)
            for default in node.args.defaults:
                self._analize_expr(default)
            for kw_default in node.args.kw_defaults:
                if kw_default is not None:
                    self._analize_expr(kw_default)
        elif isinstance(node, ClassDef):
            self._assign_symbol(node.name)
            for deco in node.decorator_list:
                self._analize_expr(deco)
            for base in node.bases:
                self._analize_expr(base)
            for kw in node.keywords:
                self._analize_expr(kw.value)
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
        elif isinstance(node, (Import, ImportFrom)):
            for alias in node.names:
                if alias.asname:
                    self._assign_symbol(alias.asname)
                else:
                    self._assign_symbol(alias.name)

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
                    self._assign_symbol(top.id)
            elif isinstance(top, NamedExpr):
                self._assign_symbol(top.target.id)
                stack.append(top.value)
            elif isinstance(top, Lambda):
                stack.extend(top.args.defaults)
                for kw_default in top.args.kw_defaults:
                    if kw_default is not None:
                        stack.append(kw_default)
                self._tmp_inner_scope_nodes.append(top)
            elif isinstance(top, _CompTypes):
                pass  # todo
            else:
                handle_generic_expr(top)

    def _assign_symbol(self, name: str) -> None:
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
        self._analyze_scope()

    def _assign_symbol(self, name: str):
        self.symbols[name] = SymbolTypeFlags.GLOBAL

    def _reference_symbol(self, name: str) -> None:
        if name not in self.symbols:
            self.symbols[name] = SymbolTypeFlags.REFERENCED_GLOBAL

    def _bind_global(self, name: str) -> None:
        pass

    def _bind_nonlocal(self, name: str) -> None:
        raise SyntaxError("nonlocal declaration not allowed at module level")


V = typing.TypeVar("V", FunctionDef, Lambda)


class _ScopeFunctionBase(Scope[V]):
    outer_scope: "Scope"
    nonlocal_reference_dict: dict[str, "_ScopeFunctionBase"]  # dst_name:src_scope

    def _assign_symbol(self, name: str) -> None:
        if (
            name in self.symbols
            and self.symbols[name] != SymbolTypeFlags.REFERENCED_GLOBAL
        ):
            return
        self.symbols[name] = SymbolTypeFlags.LOCAL

    def _reference_symbol(self, name: str) -> None:
        if name in self.symbols:
            return

        outer = self.outer_scope
        while True:
            if isinstance(outer, ScopeGlobal):
                self.symbols[name] = SymbolTypeFlags.REFERENCED_GLOBAL
                break

            while isinstance(outer, ScopeClass):
                outer = outer.outer_scope

            assert isinstance(outer, _ScopeFunctionBase)
            if name in outer.symbols:
                outer.symbols[name] |= SymbolTypeFlags.NONLOCAL_SRC
                self.symbols[name] = SymbolTypeFlags.FREE
                self.nonlocal_reference_dict[name] = outer
                break

            outer = outer.outer_scope

    def _register_function_args(self, args: arguments):
        for arg in itertools.chain(args.posonlyargs, args.args, args.kwonlyargs):
            self.symbols[arg.arg] = SymbolTypeFlags.PARAMETER
        if args.vararg is not None:
            self.symbols[args.vararg.arg] = SymbolTypeFlags.PARAMETER
        if args.kwarg is not None:
            self.symbols[args.kwarg.arg] = SymbolTypeFlags.PARAMETER


class ScopeFunction(_ScopeFunctionBase[FunctionDef]):
    def __init__(
        self, node: FunctionDef, outer_scope: Scope, global_scope: ScopeGlobal
    ) -> None:
        self.outer_scope = outer_scope
        self.nonlocal_reference_dict = {}
        super().__init__(node, global_scope)
        self._register_function_args(node.args)
        self._analyze_scope()

    def _bind_global(self, name: str) -> None:
        if name in self.symbols:
            sym = self.symbols[name]
            if sym & SymbolTypeFlags.GLOBAL:
                return
            raise SyntaxError(f"name '{name}' is assigned to before global declaration")
        else:
            self.symbols[name] = SymbolTypeFlags.GLOBAL

    def _bind_nonlocal(self, name: str) -> None:
        if name in self.symbols:
            sym = self.symbols[name]
            if sym & SymbolTypeFlags.NONLOCAL_DST:
                return
            if sym & SymbolTypeFlags.GLOBAL:
                raise SyntaxError(f"name '{name}' is nonlocal and global")
            if sym & SymbolTypeFlags.LOCAL:
                raise SyntaxError(
                    f"name '{name}' is assigned prior to nonlocal declaration"
                )
            raise SyntaxError(f"name '{name}' is used to before nonlocal declaration")

        outer = self.outer_scope
        while True:
            if isinstance(outer, ScopeGlobal):
                raise SyntaxError(f"no binding for nonlocal '{name}' found")

            if isinstance(outer, ScopeClass):
                outer = outer.outer_scope
                continue

            assert isinstance(outer, ScopeFunction)
            if name in outer.symbols:
                outer.symbols[name] |= SymbolTypeFlags.NONLOCAL_SRC
                self.symbols[name] = SymbolTypeFlags.NONLOCAL_DST
                self.nonlocal_reference_dict[name] = outer
                break

            outer = outer.outer_scope


class ScopeLambda(_ScopeFunctionBase[Lambda]):
    def __init__(
        self, node: Lambda, outer_scope: Scope, global_scope: ScopeGlobal
    ) -> None:
        self.outer_scope = outer_scope
        self.nonlocal_reference_dict = {}
        super().__init__(node, global_scope)
        self._register_function_args(node.args)
        self._analize_expr(node.body)


class ScopeClass(Scope[ClassDef]):
    outer_scope: "Scope"
    nonlocal_reference_dict: dict[str, "ScopeFunction"]  # dst_name:src_scope

    def __init__(
        self, node: ClassDef, outer_scope: Scope, global_scope: ScopeGlobal
    ) -> None:
        self.outer_scope = outer_scope
        self.nonlocal_reference_dict = {}
        super().__init__(node, global_scope)
        self._analyze_scope()


def analyze_scopes(root_node: Module) -> ScopeGlobal:
    return ScopeGlobal(root_node)


if __name__ == "__main__":
    import ast

    code = """
lambda:[a,a:=1]
"""
    scope = analyze_scopes(ast.parse(code))
    print(scope.symbols)
    print(scope.inner_scopes[0].symbols)
