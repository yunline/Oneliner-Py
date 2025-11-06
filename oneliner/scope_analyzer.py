import typing
import itertools
import enum
from ast import *

__all__ = [
    "SymbolTypeFlags",
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


_Comprehensions: typing.TypeAlias = ListComp | SetComp | DictComp | GeneratorExp

T = typing.TypeVar("T", Module, FunctionDef, ClassDef, Lambda, _Comprehensions)


class Scope(typing.Generic[T]):
    node: T
    outer_scope: "Scope"
    inner_scopes: list["Scope"]
    nonlocal_reference_dict: dict[str, "_ScopeFunctionBase"]  # dst_name:src_scope

    symbols: dict[str, SymbolTypeFlags]

    _tmp_inner_scope_nodes: list[ClassDef | FunctionDef | Lambda | _Comprehensions]

    def __init__(self, node: T) -> None:
        self.node = node
        self.inner_scopes = []
        self.symbols = {}
        self._tmp_inner_scope_nodes = []

    def _analyze_scope(self) -> None:
        # this method is for (Module, FunctionDef, ClassDef) only
        assert isinstance(self.node, (Module, FunctionDef, ClassDef))

        stack: list[stmt] = list(reversed(self.node.body))

        while stack:
            top = stack.pop()
            self._analize_stmt(top)

            if isinstance(top, (If, While, For)):
                stack.extend(reversed(top.body))
                stack.extend(reversed(top.orelse))

    def _recursive_generate_inner_scope(self) -> None:
        for inner_node in self._tmp_inner_scope_nodes:
            new_scope: Scope
            if isinstance(inner_node, FunctionDef):
                new_scope = ScopeFunction(inner_node, self)
            elif isinstance(inner_node, ClassDef):
                new_scope = ScopeClass(inner_node, self)
            elif isinstance(inner_node, Lambda):
                new_scope = ScopeLambda(inner_node, self)
            else:
                new_scope = ScopeComprehensions(inner_node, self)
            self.inner_scopes.append(new_scope)

    def _analize_stmt(self, node: stmt) -> None:
        if isinstance(node, FunctionDef):
            self._tmp_inner_scope_nodes.append(node)
            self._assign_symbol(node.name)
            for deco in node.decorator_list:
                self._analize_expr(deco)
            for default in node.args.defaults:
                self._analize_expr(default)
            for kw_default in node.args.kw_defaults:
                if kw_default is not None:
                    self._analize_expr(kw_default)
        elif isinstance(node, ClassDef):
            self._tmp_inner_scope_nodes.append(node)
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
            elif isinstance(top, (ListComp, SetComp, DictComp, GeneratorExp)):
                self._tmp_inner_scope_nodes.append(top)
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
        super().__init__(node)
        self._analyze_scope()
        self._recursive_generate_inner_scope()

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

S = typing.TypeVar("S", FunctionDef, ClassDef)

class _ScopeBlockBase(Scope[S]):
    def _bind_global(self, name: str) -> None:
        if name not in self.symbols:
            self.symbols[name] = SymbolTypeFlags.GLOBAL
            return
        sym = self.symbols[name]
        if sym & SymbolTypeFlags.GLOBAL:
            return
        if sym & SymbolTypeFlags.LOCAL:
            raise SyntaxError(f"name '{name}' is assigned to before global declaration")
        if sym & (SymbolTypeFlags.REFERENCED_GLOBAL | SymbolTypeFlags.FREE):
            raise SyntaxError(f"name '{name}' is used prior to global declaration")
        if sym & SymbolTypeFlags.PARAMETER:
            raise SyntaxError(f"name '{name}' is parameter and global")
        if sym & SymbolTypeFlags.NONLOCAL_DST:
            raise SyntaxError(f"name '{name}' is nonlocal and global")
        raise RuntimeError(f"Unable to declare name '{name}' global")

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


class ScopeFunction(_ScopeFunctionBase[FunctionDef], _ScopeBlockBase[FunctionDef]):
    def __init__(self, node: FunctionDef, outer_scope: Scope) -> None:
        self.outer_scope = outer_scope
        self.nonlocal_reference_dict = {}
        super().__init__(node)
        self._register_function_args(node.args)
        self._analyze_scope()
        self._recursive_generate_inner_scope()

class ScopeLambda(_ScopeFunctionBase[Lambda]):
    def __init__(self, node: Lambda, outer_scope: Scope) -> None:
        self.outer_scope = outer_scope
        self.nonlocal_reference_dict = {}
        super().__init__(node)
        self._register_function_args(node.args)
        self._analize_expr(node.body)
        self._recursive_generate_inner_scope()

class ScopeComprehensions(Scope[_Comprehensions]):
    reference_dict: dict[str, Scope]
    _analyzing_comp_targets: bool

    def __init__(self, node: _Comprehensions, outer_scope: Scope) -> None:
        self.outer_scope = outer_scope
        self.reference_dict = {}
        super().__init__(node)

        self._analyzing_comp_targets = True

        for gen in node.generators:
            self._analize_expr(gen.target)

        self._analyzing_comp_targets = False

        for gen in node.generators:
            self._analize_expr(gen.iter)
            for _if in gen.ifs:
                self._analize_expr(_if)

        if isinstance(node, DictComp):
            self._analize_expr(node.key)
            self._analize_expr(node.value)
        else:
            self._analize_expr(node.elt)

        self._recursive_generate_inner_scope()

    def _assign_symbol(self, name: str) -> None:
        if self._analyzing_comp_targets:
            self.symbols[name] = SymbolTypeFlags.COMPREHENSION_TARGET
            return

        outer: Scope = self
        while isinstance(outer, ScopeComprehensions):
            if (
                name in outer.symbols
                and outer.symbols[name] & SymbolTypeFlags.COMPREHENSION_TARGET
            ):
                raise SyntaxError(
                    f"assignment expression cannot rebind comprehension iteration variable '{name}'"
                )
            outer = outer.outer_scope

        self.reference_dict[name] = outer

        if isinstance(outer, ScopeGlobal):
            self.symbols[name] = SymbolTypeFlags.COMPREHENSION_ASSIGNMENT
            return

        if isinstance(outer, _ScopeFunctionBase):
            self.symbols[name] = SymbolTypeFlags.COMPREHENSION_ASSIGNMENT
            if name in outer.symbols:
                if outer.symbols[name] == SymbolTypeFlags.REFERENCED_GLOBAL:
                    outer.symbols[name] = SymbolTypeFlags.LOCAL
            else:
                outer.symbols[name] = SymbolTypeFlags.LOCAL
            return

        if isinstance(outer, ScopeClass):
            # todo
            return

    def _reference_symbol(self, name: str) -> None:
        if self._analyzing_comp_targets: # pragma: no cover
            raise RuntimeError(
                "Shall never call _reference_symbol when _analyzing_comp_targets is True"
            )

        if name in self.symbols:
            return

        self.symbols[name] = SymbolTypeFlags.COMPREHENSION_REFERENCE
        outer: Scope = self.outer_scope
        while isinstance(outer, ScopeComprehensions):
            if (
                name in outer.symbols
                and outer.symbols[name] & SymbolTypeFlags.COMPREHENSION_TARGET
            ):
                self.reference_dict[name] = outer
                return
            outer = outer.outer_scope
        self.reference_dict[name] = outer


class ScopeClass(_ScopeBlockBase[ClassDef]):
    def __init__(self, node: ClassDef, outer_scope: Scope) -> None:
        self.outer_scope = outer_scope
        self.nonlocal_reference_dict = {}
        super().__init__(node)
        self._analyze_scope()
        self._recursive_generate_inner_scope()
    
    def _assign_symbol(self, name: str) -> None:
        if name in self.symbols:
            return
        self.symbols[name] = SymbolTypeFlags.LOCAL
    
    def _reference_symbol(self, name: str) -> None:
        if name in self.symbols:
            return
        
        outer = self.outer_scope
        while 1:
            if isinstance(outer, ScopeGlobal):
                self.symbols[name] = SymbolTypeFlags.REFERENCED_GLOBAL
                return
            if isinstance(outer, ScopeFunction):
                if name in outer.symbols and outer.symbols[name] & (SymbolTypeFlags.PARAMETER|SymbolTypeFlags.LOCAL):
                    self.symbols[name] = SymbolTypeFlags.FREE
                    self.nonlocal_reference_dict[name] = outer
                return
            if isinstance(outer, ScopeClass):
                outer = outer.outer_scope
                continue
            else:
                raise RuntimeError(f"Invalid outer scope type {type(outer)}")

def analyze_scopes(root_node: Module) -> ScopeGlobal:
    return ScopeGlobal(root_node)


if __name__ == "__main__":
    import ast

    code = """
def a():
    b = 0
    def c():
        print(b)
        global b
"""
    scope = analyze_scopes(ast.parse(code))
    print(scope.inner_scopes[0].symbols)
