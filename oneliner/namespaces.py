import itertools
import symtable
import sys
import typing
from ast import *

from oneliner.config import Configs
from oneliner.reserved_identifiers import *

__all__ = [
    "generate_nsp",
    "Namespace",
    "NamespaceGlobal",
    "NamespaceFunction",
    "NamespaceClass",
]

T = typing.TypeVar("T", symtable.SymbolTable, symtable.Function, symtable.Class)


class Namespace(typing.Generic[T]):
    symt: T
    outer_nsp: "Namespace"
    inner_nsp: list["Namespace"]

    loop_stack: list["oneliner.pending_nodes._PendingLoop"]
    comp_stack: list["oneliner.expr_transform.PendingComp"]

    def __init__(self, symt: T, stack: list["Namespace"]):
        self.loop_stack = []
        self.comp_stack = []
        self.inner_nsp = []
        self.symt = symt

    def get_assign(self, name: str, value_expr: expr) -> expr:
        """
        In different namespaces,
        different types of names (global/local) have different assign methods.
        Use this to get the assign method for name except internal name
        """
        raise NotImplementedError()  # pragma: no cover

    def get_load_name(self, name: str) -> expr:
        """
        nonlocal names have different method to be load.
        Use this to get the mtehod to load the name
        """
        raise NotImplementedError()  # pragma: no cover


class NamespaceGlobal(Namespace[symtable.SymbolTable]):
    use_itertools: bool = False
    use_importlib: bool = False
    use_preset_iter_wrapper: bool = False

    configs: Configs
    expr_wraper: typing.Callable[[list[expr]], expr]

    def load_configs(self, configs: Configs):
        self.configs = configs
        self.expr_wraper = utils.get_expr_wrapper(configs)

    def get_assign(self, name: str, value_expr: expr) -> NamedExpr:
        return NamedExpr(target=Name(id=name, ctx=Store()), value=value_expr)

    def get_load_name(self, name: str) -> Name:
        return Name(id=name, ctx=Load())


class NamespaceFunction(Namespace[symtable.Function]):
    inner_nonlocal_names: set[str]  # names that is nonlocal in INNER namespace
    nonlocal_parameters: set[str]  # parameters that is nonlocal in INNER namespace
    outer_nonlocal_map: dict[str, "NamespaceFunction"]
    # keys   --> nonlocal names of THIS namespace
    # values --> where the nonlocal name was born

    is_method: bool = False  # whether the function is a method
    zero_arg_super_used: bool = False  # whether the method uses a zero-argument super

    # list of bodies of converted return nodes
    return_node_bodies: list[list[expr]]

    def __init__(self, symt: symtable.Function, stack: list[Namespace]):
        # don't push/pop the stack in this function
        super().__init__(symt, stack)

        self.return_cnt = 0

        self.return_value_expr = Name(id=ol_name(OL_RETURN_VALUE))
        self.flow_ctrl_return_expr = Name(id=ol_name(OL_RETURN))
        self.flow_ctrl_return_used = False

        self.return_node_bodies = []

        # use a dict to emulate the behavior of nonlocal
        self.nonlocal_dict_expr = Name(id=ol_name(OL_NONLOCAL_DICT))

        self.outer_nsp = stack[-1]
        self.outer_nsp.inner_nsp.append(self)
        self.inner_nonlocal_names = set()
        self.nonlocal_parameters = set()
        self.outer_nonlocal_map = {}

        if (
            isinstance(stack[-1], NamespaceClass)
            and self.symt.get_name() in stack[-1].symt.get_methods()  # type: ignore # todo:don't use get_methods
        ):
            self.is_method = True

        for nonlocal_free in itertools.chain(
            # treat 'free's as 'nonlocal's
            self.symt.get_frees(),
            self.symt.get_nonlocals(),
        ):
            if self.is_method and nonlocal_free == "__class__":
                # methods may have implicit reference the __class__ (PEP-3135)
                # which is not need here
                self.zero_arg_super_used = True
                break

            for outer in reversed(stack):
                if isinstance(outer, NamespaceClass):
                    continue
                assert isinstance(outer, NamespaceFunction)

                # free/nonlocal inevitablely exist in outer function namespace
                # so check is not need here.
                outer_symbol = outer.symt.lookup(nonlocal_free)
                if (
                    outer_symbol.is_assigned()
                    or outer_symbol.is_parameter()
                    and not outer_symbol.is_global()
                ):
                    outer.inner_nonlocal_names.add(nonlocal_free)
                    self.outer_nonlocal_map[nonlocal_free] = outer
                    if outer_symbol.is_parameter():
                        outer.nonlocal_parameters.add(nonlocal_free)
                    break
            else:
                raise RuntimeError(  # pragma: no cover
                    f"Unable to search the origin of nonlocal/free '{nonlocal_free}'"
                )

    def get_flow_ctrl_expr(self):
        self.flow_ctrl_return_used = True
        return self.flow_ctrl_return_expr

    def get_assign(self, name: str, value_expr: expr) -> expr:
        symbol = self.symt.lookup(name)
        if symbol.is_declared_global():
            return Call(
                func=Attribute(
                    value=Call(
                        func=Name(id="globals", ctx=Load()), args=[], keywords=[]
                    ),
                    attr="__setitem__",
                    ctx=Load(),
                ),
                args=[Constant(value=name), value_expr],
                keywords=[],
            )
        elif name in self.outer_nonlocal_map:
            outer = self.outer_nonlocal_map[name]
            return Call(
                func=Attribute(
                    value=outer.nonlocal_dict_expr, attr="__setitem__", ctx=Load()
                ),
                args=[Constant(value=name), value_expr],
                keywords=[],
            )
        elif name in self.inner_nonlocal_names:
            return Call(
                func=Attribute(
                    value=self.nonlocal_dict_expr, attr="__setitem__", ctx=Load()
                ),
                args=[Constant(value=name), value_expr],
                keywords=[],
            )
        else:
            return NamedExpr(
                target=Name(id=name, ctx=Store()),
                value=value_expr,
            )

    def get_load_name(self, name: str) -> expr:
        for comp in self.comp_stack:
            if name in comp.target_names:
                return Name(id=name, ctx=Load())

        if name in self.inner_nonlocal_names:
            return Subscript(
                value=self.nonlocal_dict_expr,
                slice=Constant(value=name),
                ctx=Load(),
            )
        elif name in self.outer_nonlocal_map:
            outer = self.outer_nonlocal_map[name]
            return Subscript(
                value=outer.nonlocal_dict_expr,
                slice=Constant(value=name),
                ctx=Load(),
            )
        else:  # globals or locals except free
            return Name(id=name, ctx=Load())


class NamespaceClass(Namespace[symtable.Class]):
    # NamespaceClass doesn't have inner_nonlocal_names

    outer_nonlocal_map: dict[str, "NamespaceFunction"]
    # keys   --> nonlocal names of THIS namespace
    # values --> where the nonlocal name was born

    if sys.version_info < (3, 12):
        globals_used_in_comp: set[str]  # global names used in comprehensions

    def __init__(self, symt: symtable.Class, stack: list[Namespace]):
        # don't push/pop the stack in this function
        super().__init__(symt, stack)
        self.class_member_dict_expr = Name(id=ol_name(OL_CLASS_DICT))

        self.outer_nsp = stack[-1]
        self.outer_nsp.inner_nsp.append(self)
        self.outer_nonlocal_map = {}
        if sys.version_info < (3, 12):
            self.globals_used_in_comp = set()

        for symbol in self.symt.get_symbols():
            if not (symbol.is_nonlocal() or symbol.is_free()):
                continue
            nonlocal_free: str = symbol.get_name()
            # treat 'free's as 'nonlocal's
            for outer in reversed(stack):
                if isinstance(outer, NamespaceClass):
                    continue
                assert isinstance(outer, NamespaceFunction)

                # free/nonlocal inevitablely exist in outer function namespace
                # so check is not need here.
                outer_symbol = outer.symt.lookup(nonlocal_free)
                if (
                    outer_symbol.is_assigned()
                    or outer_symbol.is_parameter()
                    and not outer_symbol.is_global()
                ):
                    outer.inner_nonlocal_names.add(nonlocal_free)
                    self.outer_nonlocal_map[nonlocal_free] = outer
                    if outer_symbol.is_parameter():
                        outer.nonlocal_parameters.add(nonlocal_free)
                    break
            else:
                raise RuntimeError(  # pragma: no cover
                    f"Unable to search the origin of nonlocal/free '{nonlocal_free}'"
                )

    def get_assign(self, name: str, value_expr: expr) -> expr:
        symbol = self.symt.lookup(name)
        if symbol.is_declared_global():
            return Call(
                func=Attribute(
                    value=Call(
                        func=Name(id="globals", ctx=Load()), args=[], keywords=[]
                    ),
                    attr="__setitem__",
                    ctx=Load(),
                ),
                args=[Constant(value=name), value_expr],
                keywords=[],
            )
        elif name in self.outer_nonlocal_map:
            outer = self.outer_nonlocal_map[name]
            return Call(
                func=Attribute(
                    value=outer.nonlocal_dict_expr, attr="__setitem__", ctx=Load()
                ),
                args=[Constant(value=name), value_expr],
                keywords=[],
            )
        else:
            # assign to a class member
            return Call(
                func=Attribute(
                    value=self.class_member_dict_expr, attr="__setitem__", ctx=Load()
                ),
                args=[Constant(value=name), value_expr],
                keywords=[],
            )

    def get_load_name(self, name: str) -> expr:
        for comp in self.comp_stack:
            if name in comp.target_names:
                return Name(id=name, ctx=Load())

        if sys.version_info < (3, 12) and name in self.globals_used_in_comp:
            return Name(id=name, ctx=Load())

        symbol = self.symt.lookup(name)
        if name in self.outer_nonlocal_map:
            outer = self.outer_nonlocal_map[name]
            return Subscript(
                value=outer.nonlocal_dict_expr,
                slice=Constant(value=name),
                ctx=Load(),
            )
        elif symbol.is_global():
            return Name(id=name, ctx=Load())
        else:
            # a class member
            return Subscript(
                value=self.class_member_dict_expr,
                slice=Constant(value=name),
                ctx=Load(),
            )


if sys.version_info < (3, 12):

    def _comp_check(symt: symtable.Function):
        if symt.get_name() not in ["listcomp", "genexpr", "setcomp", "dictcomp"]:
            return False
        if ".0" not in symt.get_parameters():
            return False
        return True


def update_globals_from_lambda_or_comp(symt: symtable.Function, stack: list[Namespace]):
    if not isinstance(stack[-1], NamespaceClass):
        return

    _globals: set[str] = set()
    comp_stack = [symt]
    while comp_stack:
        symt = comp_stack.pop()
        for symbol in symt.get_symbols():
            if symbol.is_global():
                _globals.add(symbol.get_name())
        for child_symt in symt.get_children():
            assert isinstance(child_symt, symtable.Function)
            comp_stack.append(child_symt)
    stack[-1].globals_used_in_comp.update(_globals)


def generate_nsp(symt: symtable.SymbolTable, configs: Configs):
    walk_stack = []
    generate_stack: list[Namespace] = []
    root = NamespaceGlobal(symt, generate_stack)
    root.load_configs(configs)
    generate_stack.append(root)

    walk_stack.append(iter(symt.get_children()))
    while walk_stack:
        try:
            child_symt = next(walk_stack[-1])
        except StopIteration:
            walk_stack.pop()
            generate_stack.pop()
        else:
            if isinstance(child_symt, symtable.Function):
                if child_symt.get_name() == "lambda":
                    update_globals_from_lambda_or_comp(child_symt, generate_stack)
                    continue
                if sys.version_info < (3, 12):
                    if _comp_check(child_symt):
                        update_globals_from_lambda_or_comp(child_symt, generate_stack)
                        continue

                generate_stack.append(NamespaceFunction(child_symt, generate_stack))
            elif isinstance(child_symt, symtable.Class):
                generate_stack.append(NamespaceClass(child_symt, generate_stack))
            else:  # pragma: no cover
                raise RuntimeError("Unknown type of child symbol table")
            walk_stack.append(iter(child_symt.get_children()))
    return root


# fix error caused by circular import
import oneliner.expr_transform
import oneliner.pending_nodes
