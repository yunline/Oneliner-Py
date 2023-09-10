import itertools
import symtable
from ast import *

from oneliner.reserved_identifiers import *

__all__ = [
    "generate_nsp",
    "Namespace",
    "NamespaceGlobal",
    "NamespaceFunction",
    "NamespaceClass",
]


class Namespace:
    symt: symtable.SymbolTable
    outer_nsp: "Namespace"
    inner_nsp: list["Namespace"]

    @classmethod
    def _generate(cls):
        raise NotImplementedError()  # pragma: no cover

    def __init__(self):
        self.loop_stack: list["pending_nodes._PendingLoop"] = []
        self.inner_nsp = []

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


class NamespaceGlobal(Namespace):
    @classmethod
    def _generate(cls, symt: symtable.SymbolTable):
        self = cls()
        self.symt = symt
        return self

    def __init__(self):
        super().__init__()

        self.use_itertools = False
        self.use_importlib = False
        self.use_preset_iter_wrapper = False

    def get_assign(self, name: str, value_expr: expr) -> NamedExpr:
        return NamedExpr(target=Name(id=name, ctx=Store()), value=value_expr)

    def get_load_name(self, name: str) -> Name:
        return Name(id=name, ctx=Load())


class NamespaceFunction(Namespace):
    inner_nonlocal_names: set[str]  # names that is nonlocal in INNER namespace
    nonlocal_parameters: set[str]  # parameters that is nonlocal in INNER namespace
    outer_nonlocal_map: dict[str, "NamespaceFunction"]
    # keys   --> nonlocal names of THIS namespace
    # values --> where the nonlocal name was born

    is_method: bool  # whether the function is a method
    zero_arg_super_used: bool  # whether the method uses a zero-argument super

    symt: symtable.Function  # symbol table of this namespace

    @classmethod
    def _generate(cls, symt: symtable.Function, stack: list[Namespace]):
        # don't push/pop the stack in this function

        self = cls()
        self.symt = symt

        self.outer_nsp = stack[-1]
        self.outer_nsp.inner_nsp.append(self)
        self.inner_nonlocal_names = set()
        self.nonlocal_parameters = set()
        self.outer_nonlocal_map = {}
        self.is_method = False
        self.zero_arg_super_used = False

        if (
            isinstance(stack[-1], NamespaceClass)
            and self.symt.get_name() in stack[-1].symt.get_methods()
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

        return self

    def __init__(self):
        super().__init__()

        self.return_cnt = 0

        self.return_value_expr = Name(id=ol_name(OL_RETURN_VALUE))
        self.flow_ctrl_return_expr = Name(id=ol_name(OL_RETURN))
        self.flow_ctrl_return_used = False
        self.return_node_bodies: list[
            list[AST]
        ] = []  # list of bodies of converted return nodes

        # use a dict to emulate the behavior of nonlocal
        self.nonlocal_dict_expr = Name(id=ol_name(OL_NONLOCAL_DICT))

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


class NamespaceClass(Namespace):
    symt: symtable.Class

    # NamespaceClass doesn't have inner_nonlocal_names

    outer_nonlocal_map: dict[str, "NamespaceFunction"]
    # keys   --> nonlocal names of THIS namespace
    # values --> where the nonlocal name was born

    @classmethod
    def _generate(cls, symt: symtable.Class, stack: list[Namespace]):
        # don't push/pop the stack in this function

        self = cls()
        self.symt = symt

        self.outer_nsp = stack[-1]
        self.outer_nsp.inner_nsp.append(self)
        self.outer_nonlocal_map = {}

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

        return self

    def __init__(self):
        super().__init__()
        self.class_member_dict_expr = Name(id=ol_name(OL_CLASS_DICT))

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


def generate_nsp(symt: symtable.SymbolTable):
    walk_stack = []
    root = NamespaceGlobal._generate(symt)
    generate_stack: list[Namespace] = [root]

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
                    continue
                generate_stack.append(
                    NamespaceFunction._generate(child_symt, generate_stack)
                )
                walk_stack.append(iter(child_symt.get_children()))
            elif isinstance(child_symt, symtable.Class):
                generate_stack.append(
                    NamespaceClass._generate(child_symt, generate_stack)
                )
                walk_stack.append(iter(child_symt.get_children()))
            else:  # pragma: no cover
                raise RuntimeError("Unknown type of child symbol table")
    return root


# fix error caused by circular import
import oneliner.pending_nodes as pending_nodes
