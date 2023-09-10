from ast import *

from oneliner.namespaces import Namespace

__all__ = [
    "expr_transf",
]


class PendingExprGeneric:
    def __init__(self, node: expr):
        self.node = node
        self.converted_dict: dict[str, expr | list[expr]] = {}

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


class PendingNamedExpr(PendingExprGeneric):
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


class PendingName(PendingExprGeneric):
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


class ExpressionTransformer:
    def __init__(self, nsp: Namespace):
        self.pending_stack: list[PendingExprGeneric] = []
        self.nsp = nsp

    def get_pending(self, node: expr) -> PendingExprGeneric:
        if isinstance(node, NamedExpr):
            return PendingNamedExpr(node, self.nsp)
        elif isinstance(node, Name):
            return PendingName(node, self.nsp)
        else:
            return PendingExprGeneric(node)

    def cvt(self, node: expr):
        unconverted = node
        converted = None
        while True:
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
