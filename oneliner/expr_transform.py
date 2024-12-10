import typing
from ast import *

from oneliner.namespaces import Namespace

__all__ = [
    "expr_transf",
]

_CompNode: typing.TypeAlias = ListComp | SetComp | DictComp | GeneratorExp
T = typing.TypeVar("T", expr, NamedExpr, Name, _CompNode)


class PendingExprGeneric(typing.Generic[T]):
    node: T
    converted_dict: dict[str, typing.Any]

    def __init__(self, node: T):
        self.node = node
        self.converted_dict = {}

        self.iter_fields = self._iter_fields()

    def _iter_fields(self):
        for field_name in self.node._fields:
            if not hasattr(self.node, field_name):
                continue
            field = getattr(self.node, field_name)
            if isinstance(field, expr):
                self.converted_dict[field_name] = yield field
            elif isinstance(field, list):
                converted_list = self.converted_dict[field_name] = []
                for _node in field:
                    converted_list.append((yield _node))
            else:
                self.converted_dict[field_name] = field

    def get_result(self) -> expr:
        return type(self.node)(**self.converted_dict)


class PendingExpr(PendingExprGeneric[expr]):
    pass


class PendingNamedExpr(PendingExprGeneric[NamedExpr]):
    def __init__(self, node: NamedExpr, nsp: Namespace):
        self.node = node
        self.nsp = nsp

        self.value = None

        self.iter_fields = self._iter_fields()

    def _iter_fields(self):
        self.value = yield self.node.value

    def get_result(self) -> expr:
        assert self.value is not None
        result = self.nsp.get_assign(self.node.target.id, self.value)
        if not isinstance(result, NamedExpr):
            result = Subscript(
                value=List(
                    elts=[
                        result,
                        self.node.target,
                    ],
                    ctx=Load(),
                ),
                slice=Constant(value=-1),
                ctx=Load(),
            )

        return result


class PendingName(PendingExprGeneric[Name]):
    def __init__(self, node: Name, nsp: Namespace):
        self.node = node
        self.nsp = nsp

        self.iter_fields = self._iter_fields()

    def _iter_fields(self):
        return
        yield

    def get_result(self) -> expr:
        if isinstance(self.node.ctx, Store):
            return Name(id=self.node.id, ctx=Store())
        return self.nsp.get_load_name(self.node.id)


class PendingComp(PendingExprGeneric[_CompNode]):
    target_names: set[str]
    node: _CompNode

    def __init__(self, node: _CompNode, nsp: Namespace):
        super().__init__(node)
        self.nsp = nsp
        self.target_names = set()

        for comp in self.node.generators:
            self.get_comp_target_names(comp.target)

        self.nsp.comp_stack.append(self)

    def get_result(self) -> expr:
        assert self.nsp.comp_stack[-1] is self
        self.nsp.comp_stack.pop()

        return super().get_result()

    def get_comp_target_names(self, target):
        """
        Recursion warning
        """
        if isinstance(target, Name):
            self.target_names.add(target.id)
        elif isinstance(target, (Tuple, List)):
            for sub_target in target.elts:
                self.get_comp_target_names(sub_target)
        else:  # pragma: no cover
            raise RuntimeError("Unknown comprehension target")


class ExpressionTransformer:
    def __init__(self, nsp: Namespace):
        self.pending_stack: list[PendingExprGeneric] = []
        self.nsp = nsp

    def get_pending(self, node: expr) -> PendingExprGeneric:
        if isinstance(node, NamedExpr):
            return PendingNamedExpr(node, self.nsp)
        elif isinstance(node, Name):
            return PendingName(node, self.nsp)
        elif isinstance(node, (ListComp, SetComp, DictComp, GeneratorExp)):
            return PendingComp(node, self.nsp)
        else:
            return PendingExpr(node)

    def cvt(self, node: expr):
        unconverted: expr | None = node
        converted = None
        while True:
            assert unconverted is not None
            pending_node = self.get_pending(unconverted)
            self.pending_stack.append(pending_node)
            unconverted = None
            while unconverted is None:
                try:
                    unconverted = self.pending_stack[-1].iter_fields.send(converted)
                    converted = None
                except StopIteration:
                    converted = self.pending_stack.pop().get_result()
                    if len(self.pending_stack) == 0:
                        return converted


def expr_transf(nsp: Namespace, node: expr):
    return ExpressionTransformer(nsp).cvt(node)
