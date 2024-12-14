import typing
from ast import *

import oneliner.utils as utils
from oneliner.expr_transform import expr_transf
from oneliner.namespaces import (
    Namespace,
    NamespaceClass,
    NamespaceFunction,
    NamespaceGlobal,
)
from oneliner.reserved_identifiers import *

__all__ = [
    "PendingNode",
    "PendingModule",
    "PendingExpr",
    "PendingIf",
    "PendingWhile",
    "PendingFor",
    "PendingBreak",
    "PeindingContinue",
    "PendingPass",
    "PendingAssign",
    "PendingAugAssign",
    "PendingFunctionDef",
    "PendingReturn",
    "PendingGlobal",
    "PendingNonlocal",
    "PendingClassDef",
    "PendingImport",
    "PendingImportFrom",
]

T = typing.TypeVar(
    "T",
    Module,
    Expr,
    If,
    While,
    For,
    Break,
    Continue,
    Pass,
    Assign | AnnAssign,
    AugAssign,
    FunctionDef,
    Return,
    Global,
    Nonlocal,
    ClassDef,
    Import,
    ImportFrom,
)
L = typing.TypeVar("L", While, For)


class PendingNode(typing.Generic[T]):
    node: T

    def __init__(self, node: T, nsp: Namespace, nsp_global: NamespaceGlobal):
        self.iter_node = self._iter_nodes()
        self.nsp = nsp
        self.nsp_global = nsp_global
        self.node = node

    def get_result(self) -> list[expr]:
        raise NotImplementedError()  # pragma: no cover

    def _iter_nodes(self) -> typing.Generator[AST, list[expr], None]:
        return None
        yield AST()

    has_internal_namespace: bool = False

    def get_internal_namespace(self) -> Namespace:
        raise NotImplementedError()  # pragma: no cover


class PendingModule(PendingNode[Module]):
    converted_body: list[expr]

    def __init__(self, node: Module, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)
        self.converted_body = []

    def _iter_nodes(self) -> typing.Generator[AST, list[expr], None]:
        for node in self.node.body:
            self.converted_body.extend((yield node))

    def _insert_import_lib(self, libname, asname):
        import_itertools_ast = NamedExpr(
            target=Name(id=asname, ctx=Store()),
            value=Call(
                func=Name(id="__import__", ctx=Load()),
                args=[Constant(value=libname)],
                keywords=[],
            ),
        )
        self.converted_body.insert(0, import_itertools_ast)

    def get_result(self) -> list[expr]:
        if self.nsp_global.use_itertools:
            self._insert_import_lib("itertools", "itertools")
        if self.nsp_global.use_importlib:
            self._insert_import_lib("importlib", "importlib")

        if self.nsp_global.use_preset_iter_wrapper:
            from .presets import iter_wrapper_body

            self.converted_body.insert(0, iter_wrapper_body)

        return self.converted_body


class PendingExpr(PendingNode[Expr]):
    def get_result(self) -> list[expr]:
        return [expr_transf(self.nsp, self.node.value)]


class _PendingCompoundStmt(PendingNode[T]):
    """
    CompoundStmt:
        PendingIf
        PendingWhile
        PendingFor
        PendingFunctionDef
        PendingClassDef

    They have some common behaviors
    So _PendingCompoundStmt is created
    """

    def _iter_branch(
        self,
        converted_branch: list[expr],
        branch: list[stmt],
        get_interrupt_cnt: typing.Callable[[], int],
        get_flow_control_expr: typing.Callable[[], expr],
    ) -> typing.Generator[AST, list[expr], None]:
        initial_interrupt_cnt = get_interrupt_cnt()

        converting: list[expr] = []
        stack = [converting]
        for node in branch:
            if get_interrupt_cnt() > initial_interrupt_cnt:
                converting = []
                stack.append(converting)
                initial_interrupt_cnt = get_interrupt_cnt()

            converting.extend((yield node))

            if isinstance(node, (Break, Continue, Return)):
                # remove nodes after an "interrupt operation"
                # since they never run
                break

        while len(stack) > 1:
            # wrap nodes with an "if" to check interrupt at run time
            wrapped = stack.pop()
            stack[-1].append(
                IfExp(
                    test=UnaryOp(op=Not(), operand=get_flow_control_expr()),
                    body=self.nsp_global.expr_wraper(wrapped),
                    orelse=Constant(value=...),
                )
            )
        converted_branch.extend(stack[0])


class PendingIf(_PendingCompoundStmt[If]):
    converted_body: list[expr]
    converted_orelse: list[expr]

    def __init__(self, node: If, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)

        self.converted_body = []
        self.converted_orelse = []

    def get_result(self) -> list[expr]:
        test = expr_transf(self.nsp, self.node.test)
        body = self.nsp_global.expr_wraper(self.converted_body)
        orelse = self.nsp_global.expr_wraper(self.converted_orelse)
        if self.nsp_global.configs.if_style == "short_circuit":
            if len(self.converted_orelse) > 0:
                body_or_true = BoolOp(op=Or(), values=[body, Constant(value=1)])
                semi_if = BoolOp(op=And(), values=[test, body_or_true])
                return [BoolOp(op=Or(), values=[semi_if, orelse])]
            else:
                return [BoolOp(op=And(), values=[test, body])]
        else:  # if_style=="if_expr"
            return [IfExp(test=test, body=body, orelse=orelse)]

    def _iter_nodes(self) -> typing.Generator[AST, list[expr], None]:
        if self.nsp.loop_stack:
            # if inside a loop
            get_interrupt_cnt = lambda: self.nsp.loop_stack[-1].interrupt_cnt
            get_flow_control_expr = self.nsp.loop_stack[-1].get_flow_ctrl_expr
        elif isinstance(self.nsp, NamespaceFunction):
            # if inside a function
            self.nsp: NamespaceFunction  # fix type checker error
            get_interrupt_cnt = lambda: self.nsp.return_cnt
            get_flow_control_expr = self.nsp.get_flow_ctrl_expr
        else:
            get_interrupt_cnt = lambda: 0
            get_flow_control_expr = utils.never_call

        yield from self._iter_branch(
            self.converted_body,
            self.node.body,
            get_interrupt_cnt,
            get_flow_control_expr,
        )
        yield from self._iter_branch(
            self.converted_orelse,
            self.node.orelse,
            get_interrupt_cnt,
            get_flow_control_expr,
        )


class _PendingLoop(_PendingCompoundStmt[L]):
    node: L  # Original node
    flow_ctrl_interrupt_expr: Name
    flow_ctrl_interrupt_used: bool
    interrupt_node_bodies: list[
        list[expr]
    ]  # list of bodies of converted return/break/continue nodes
    converted_body: list[expr]  # converted body branch
    converted_orelse: list[expr]  # converted orelse branch
    interrupt_cnt: int = 0  # Continue, Break and Return will increase this counter
    break_cnt: int = 0  # Break and Return will increase this counter

    def get_flow_ctrl_expr(self):
        self.flow_ctrl_interrupt_used = True
        return self.flow_ctrl_interrupt_expr

    def _iter_nodes(self) -> typing.Generator[AST, list[expr], None]:
        yield from self._iter_branch(
            self.converted_body,
            self.node.body,
            lambda: self.interrupt_cnt,
            self.get_flow_ctrl_expr,
        )
        # body finish, pop from loop stack
        self.nsp.loop_stack.pop()

        if self.nsp.loop_stack:
            # if inside a loop
            get_interrupt_cnt = lambda: self.nsp.loop_stack[-1].interrupt_cnt
            get_flow_control_expr = self.nsp.loop_stack[-1].get_flow_ctrl_expr
        elif isinstance(self.nsp, NamespaceFunction):
            # if inside a function
            self.nsp: NamespaceFunction  # fix type checker error
            get_interrupt_cnt = lambda: self.nsp.return_cnt
            get_flow_control_expr = self.nsp.get_flow_ctrl_expr
        else:
            get_interrupt_cnt = lambda: 0
            get_flow_control_expr = utils.never_call

        yield from self._iter_branch(
            self.converted_orelse,
            self.node.orelse,
            get_interrupt_cnt,
            get_flow_control_expr,
        )


class PendingWhile(_PendingLoop[While]):
    def __init__(self, node: While, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)

        self.converted_body = []
        self.converted_orelse = []

        # flow-control vars
        self.flow_ctrl_break_expr = Name(id=ol_name(OL_BREAK))
        self.flow_ctrl_interrupt_expr = Name(id=ol_name(OL_INTERRUPT))
        self.flow_ctrl_interrupt_used = False
        self.interrupt_node_bodies = []

        self.nsp.loop_stack.append(self)

        self.nsp_global.use_itertools = True

    def get_result(self) -> list[expr]:
        while_loop_final: list[expr] = []

        # if there is break, reset the flow-control var
        # and enable itertools
        if self.break_cnt:
            while_loop_final.append(
                NamedExpr(
                    target=self.flow_ctrl_break_expr,
                    value=Constant(value=False),
                )
            )

        # init the interrupt flow-control var
        if self.flow_ctrl_interrupt_used:
            self.converted_body.insert(
                0,
                NamedExpr(
                    target=self.flow_ctrl_interrupt_expr,
                    value=Constant(value=False),
                ),
            )
            # inject flow_ctrl_interrupt_expr to interrupt nodes
            for interrupt_body in self.interrupt_node_bodies:
                interrupt_body.append(
                    NamedExpr(
                        target=self.flow_ctrl_interrupt_expr,
                        value=Constant(value=True),
                    )
                )

        # add additional check in "test"
        # if there is a break
        if self.break_cnt:
            while_loop_test = BoolOp(
                op=And(),
                values=[
                    UnaryOp(op=Not(), operand=self.flow_ctrl_break_expr),
                    expr_transf(self.nsp, self.node.test),
                ],
            )
        else:
            while_loop_test = expr_transf(self.nsp, self.node.test)

        # "orelse" runs if there's no break
        while_loop_orelse: expr
        if self.break_cnt:
            while_loop_orelse = IfExp(
                test=UnaryOp(op=Not(), operand=self.flow_ctrl_break_expr),
                body=self.nsp_global.expr_wraper(self.converted_orelse),
                orelse=Constant(value=...),
            )
        else:
            while_loop_orelse = self.nsp_global.expr_wraper(self.converted_orelse)

        # the main body of the oneliner while loop
        while_loop_body = ListComp(
            elt=self.nsp_global.expr_wraper(self.converted_body),
            generators=[
                comprehension(
                    target=Name(id="_", ctx=Store()),
                    iter=Call(
                        func=Attribute(
                            value=Name(id="itertools", ctx=Load()),
                            attr="takewhile",
                            ctx=Load(),
                        ),
                        args=[
                            Lambda(
                                args=arguments(
                                    posonlyargs=[],
                                    args=[arg(arg="_")],
                                    kwonlyargs=[],
                                    kw_defaults=[],
                                    defaults=[],
                                ),
                                body=while_loop_test,
                            ),
                            Call(
                                func=Attribute(
                                    value=Name(id="itertools", ctx=Load()),
                                    attr="count",
                                    ctx=Load(),
                                ),
                                args=[],
                                keywords=[],
                            ),
                        ],
                        keywords=[],
                    ),
                    ifs=[],
                    is_async=0,
                )
            ],
        )

        # assemble all parts together and return
        while_loop_final.append(while_loop_body)
        # if orelse is not empty, add orelse
        if self.converted_orelse:
            while_loop_final.append(while_loop_orelse)

        return while_loop_final


class PendingFor(_PendingLoop[For]):
    def __init__(self, node: For, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)

        self.converted_body = []
        self.converted_orelse = []

        # flow-control vars
        self.flow_ctrl_wrapped_iter_expr = Name(id=ol_name(OL_WRAPPED_ITER))
        self.flow_ctrl_interrupt_expr = Name(id=ol_name(OL_INTERRUPT))
        self.flow_ctrl_interrupt_used = False
        self.interrupt_node_bodies = []

        self.nsp.loop_stack.append(self)

    def get_result(self) -> list[expr]:
        # if no break/continue/return used
        # use the simplest list comprehension
        if self.interrupt_cnt == 0 and len(self.node.orelse) == 0:
            return [
                ListComp(
                    elt=self.nsp_global.expr_wraper(self.converted_body),
                    generators=[
                        comprehension(
                            target=self.node.target,
                            iter=expr_transf(self.nsp, self.node.iter),
                            ifs=[],
                            is_async=0,
                        )
                    ],
                )
            ]

        for_loop_final: list[expr] = []

        # init the flow-control vars
        if self.flow_ctrl_interrupt_used:
            self.converted_body.insert(
                0,
                NamedExpr(
                    target=self.flow_ctrl_interrupt_expr,
                    value=Constant(value=False),
                ),
            )
            # inject flow_ctrl_interrupt_expr to interrupt nodes
            for interrupt_body in self.interrupt_node_bodies:
                interrupt_body.append(
                    NamedExpr(
                        target=self.flow_ctrl_interrupt_expr,
                        value=Constant(value=True),
                    )
                )

        # we don't need use iter_wrapper
        # if we don't use break
        if self.break_cnt == 0:
            for_loop_iter = expr_transf(self.nsp, self.node.iter)
        else:
            from .presets import iter_wrapper_name

            self.nsp_global.use_preset_iter_wrapper = True
            for_loop_iter = self.flow_ctrl_wrapped_iter_expr
            iter_wrapper_instance = NamedExpr(
                target=self.flow_ctrl_wrapped_iter_expr,
                value=Call(
                    func=iter_wrapper_name,
                    args=[expr_transf(self.nsp, self.node.iter)],
                    keywords=[],
                ),
            )
            for_loop_final.append(iter_wrapper_instance)

        # "orelse" runs if there's no break
        for_loop_orelse: expr
        if self.break_cnt:
            for_loop_orelse = IfExp(
                test=UnaryOp(
                    op=Not(),
                    operand=Attribute(
                        value=self.flow_ctrl_wrapped_iter_expr,
                        attr="_break",
                        ctx=Load(),
                    ),
                ),
                body=self.nsp_global.expr_wraper(self.converted_orelse),
                orelse=Constant(value=...),
            )
        else:
            for_loop_orelse = self.nsp_global.expr_wraper(self.converted_orelse)

        # the main body of the oneliner for loop
        for_loop_body = ListComp(
            elt=self.nsp_global.expr_wraper(self.converted_body),
            generators=[
                comprehension(
                    target=self.node.target,
                    iter=for_loop_iter,
                    ifs=[],
                    is_async=0,
                )
            ],
        )

        # assemble all parts together and return

        for_loop_final.append(for_loop_body)
        # if orelse is not empty, add orelse
        if self.converted_orelse:
            for_loop_final.append(for_loop_orelse)

        return for_loop_final


class PendingBreak(PendingNode[Break]):
    def __init__(self, node: Break, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)
        if len(self.nsp.loop_stack) == 0:
            raise SyntaxError(
                utils.ast_debug_info(node) + "'break' is not inside a loop"
            )

        self.loop = self.nsp.loop_stack[-1]
        self.loop.break_cnt += 1
        self.loop.interrupt_cnt += 1

    def get_result(self) -> list[expr]:
        return_value: list[expr] = []
        if isinstance(self.loop, PendingWhile):
            return_value.append(
                NamedExpr(
                    target=self.loop.flow_ctrl_break_expr,
                    value=Constant(value=True),
                )
            )
        elif isinstance(self.loop, PendingFor):
            return_value.append(
                Call(
                    func=Name(id="setattr", ctx=Load()),
                    args=[
                        self.loop.flow_ctrl_wrapped_iter_expr,
                        Constant(value="_break"),
                        Constant(value=True),
                    ],
                    keywords=[],
                )
            )
        self.loop.interrupt_node_bodies.append(return_value)
        return [List(elts=return_value, ctx=Load())]


class PeindingContinue(PendingNode[Continue]):
    def __init__(self, node: Continue, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)
        if len(self.nsp.loop_stack) == 0:
            raise SyntaxError(
                utils.ast_debug_info(node) + "'continue' is not inside a loop"
            )

        self.loop = self.nsp.loop_stack[-1]
        self.loop.interrupt_cnt += 1

    def get_result(self) -> list[expr]:
        return_value: list[expr] = []
        self.loop.interrupt_node_bodies.append(return_value)
        return [List(elts=return_value, ctx=Load())]


class PendingPass(PendingNode[Pass]):
    def get_result(self) -> list[expr]:
        return [Constant(value=...)]


class PendingAssign(PendingNode[Assign | AnnAssign]):
    def assign_auto(self, target: AST, value: expr) -> list[expr]:
        if isinstance(target, Name):
            return [self.assign_name(target, value)]
        elif isinstance(target, Attribute):
            return [self.assign_attribute(target, value)]
        elif isinstance(target, Subscript):
            return [self.assign_subscript(target, value)]
        elif isinstance(target, (Tuple, List)):
            return self.assign_tuple_list(target, value)
        else:
            raise NotImplementedError(f"Unknown assignment target: {type(target)}")

    def assign_name(self, target: Name, value: expr):
        return self.nsp.get_assign(target.id, value)

    def assign_subscript(self, target: Subscript, value: expr):
        _slice = target.slice
        if isinstance(_slice, Slice):
            _slice = utils.convert_slice(_slice)

        return Call(
            func=Attribute(
                value=expr_transf(self.nsp, target.value),
                attr="__setitem__",
                ctx=Load(),
            ),
            args=[_slice, value],
            keywords=[],
        )

    def assign_attribute(self, target: Attribute, value: expr) -> expr:
        return Call(
            func=Name(id="setattr", ctx=Load()),
            args=[
                expr_transf(self.nsp, target.value),
                Constant(value=target.attr),
                value,
            ],
            keywords=[],
        )

    def assign_tuple_list(self, target: Tuple | List, value: expr) -> list[expr]:
        """
        Recursion warning
        """
        return_list = []
        have_starred = False
        value_subscript: expr
        slice_upper: Constant | None
        for index, sub_target in enumerate(target.elts):
            if isinstance(sub_target, Starred):
                if have_starred:
                    raise SyntaxError(
                        utils.ast_debug_info(sub_target)
                        + "multiple starred expressions in assignment"
                    )
                have_starred = True

                sub_target = sub_target.value

                slice_upper = Constant(value=index - len(target.elts) + 1)
                if slice_upper.value == 0:
                    slice_upper = None

                value_subscript = Call(
                    func=Name(id="list", ctx=Load()),
                    args=[
                        Subscript(
                            value=value,
                            slice=Slice(
                                lower=Constant(value=index),
                                upper=slice_upper,
                            ),
                            ctx=Load(),
                        )
                    ],
                    keywords=[],
                )
            else:
                if not have_starred:
                    _slice = Constant(value=index)
                else:
                    _slice = Constant(value=index - len(target.elts))

                value_subscript = Subscript(
                    value=value,
                    slice=_slice,
                    ctx=Load(),
                )

            return_list.extend(self.assign_auto(sub_target, value_subscript))
        return return_list

    def get_result(self) -> list[expr]:
        if self.node.value is None:
            return []

        return_list: list[expr] = []
        assign_value = expr_transf(self.nsp, self.node.value)

        assign_targets: list[expr]
        if isinstance(self.node, AnnAssign):
            assign_targets = [self.node.target]
        else:
            assign_targets = self.node.targets

        if len(assign_targets) == 1 and not isinstance(
            assign_targets[0], (Tuple, List)
        ):
            # if there is only one target (not tuple or list)
            # wo don't need tmp var
            return_value = self.assign_auto(assign_targets[0], assign_value)
            assert len(return_value) == 1
            return return_value

        # save the assign value to a tmp var
        # to make sure the value expr only runs once.
        tmp_value_name = Name(id=ol_name(OL_ASSIGN_TMP))
        return_list.append(
            NamedExpr(target=tmp_value_name, value=assign_value),
        )
        for target in assign_targets:
            return_list.extend(self.assign_auto(target, tmp_value_name))

        return return_list


class PendingAugAssign(PendingNode[AugAssign]):
    _op_dict: dict[type[operator], str] = {
        Add: "__iadd__",
        BitAnd: "__iand__",
        FloorDiv: "__ifloordiv__",
        LShift: "__ilshift__",
        Mod: "__imod__",
        Mult: "__imul__",
        MatMult: "__imatmul__",
        BitOr: "__ior__",
        Pow: "__ipow__",
        RShift: "__irshift__",
        Sub: "__isub__",
        Div: "__itruediv__",
        BitXor: "__ixor__",
    }

    def _aug_assign_expr(
        self, target: expr, op: operator, value: expr, fallback: expr | None = None
    ) -> expr:
        op_name = self._op_dict[type(op)]
        if fallback is None:
            assert isinstance(target, Name)
            fallback = NamedExpr(
                target=target, value=BinOp(left=target, op=op, right=value)
            )
        return IfExp(
            test=Call(
                func=Name(id="hasattr", ctx=Load()),
                args=[target, Constant(value=op_name)],
                keywords=[],
            ),
            body=Call(
                func=Attribute(value=target, attr=op_name, ctx=Load()),
                args=[value],
                keywords=[],
            ),
            orelse=fallback,
        )

    def get_result(self) -> list[expr]:
        return_list: list[expr] = []
        tmp_target_name = Name(id=ol_name(OL_AUGASSIGN_TMP))
        assign_value = expr_transf(self.nsp, self.node.value)
        if isinstance(self.node.target, Name):
            target = self.nsp.get_load_name(self.node.target.id)
            return [
                self._aug_assign_expr(
                    target,
                    self.node.op,
                    assign_value,
                    fallback=self.nsp.get_assign(
                        self.node.target.id,
                        BinOp(left=target, op=self.node.op, right=assign_value),
                    ),
                )
            ]
        elif isinstance(self.node.target, Subscript):
            # todo: could be optimized if slice is const
            tmp_slice_name = Name(id=ol_name(OL_AUGASSIGN_SLICE_TMP))
            target = self.node.target
            subscript_parent = expr_transf(self.nsp, target.value)

            slice_expr = target.slice
            if isinstance(slice_expr, Slice):
                slice_expr = utils.convert_slice(slice_expr)

            # save slice expr to a tmp
            return_list.append(
                NamedExpr(
                    target=tmp_slice_name,
                    value=expr_transf(self.nsp, slice_expr),
                )
            )

            # load subscript value to a tmp
            return_list.append(
                NamedExpr(
                    target=tmp_target_name,
                    value=Subscript(
                        value=subscript_parent,
                        slice=tmp_slice_name,
                        ctx=Load(),
                    ),
                )
            )

            # aug assign to tmp
            _assign_body = self._aug_assign_expr(
                tmp_target_name, self.node.op, assign_value
            )

            # assign the tmp back to original subscript
            return_list.append(
                Call(
                    func=Attribute(
                        value=subscript_parent,
                        attr="__setitem__",
                        ctx=Load(),
                    ),
                    args=[tmp_slice_name, _assign_body],
                    keywords=[],
                )
            )
        elif isinstance(self.node.target, Attribute):
            target = self.node.target
            attr_parent = expr_transf(self.nsp, target.value)
            return_list.append(
                NamedExpr(
                    target=tmp_target_name,
                    value=Attribute(
                        value=attr_parent,
                        attr=target.attr,
                        ctx=Load(),
                    ),
                )
            )
            _assign_body = self._aug_assign_expr(
                tmp_target_name, self.node.op, assign_value
            )
            return_list.append(
                Call(
                    func=Name(id="setattr", ctx=Load()),
                    args=[
                        attr_parent,
                        Constant(value=target.attr),
                        _assign_body,
                    ],
                    keywords=[],
                )
            )
        else:
            raise NotImplementedError(
                f"Unknown augmented assignment target: {type(self.node.target)}"
            )
        return return_list


class PendingFunctionDef(_PendingCompoundStmt[FunctionDef]):
    has_internal_namespace = True
    internal_nsp: NamespaceFunction
    converted_body: list[expr]

    def __init__(self, node: FunctionDef, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)

        for tmp_nsp in self.nsp.inner_nsp:
            if (
                tmp_nsp.symt.get_lineno() == node.lineno
                and tmp_nsp.symt.get_name() == node.name
            ):
                assert isinstance(tmp_nsp, NamespaceFunction)
                self.internal_nsp = tmp_nsp
                break
        else:
            raise RuntimeError("Namespace not found")

        # copy args and filter annotations
        original_args = node.args
        self.converted_args = converted_args = arguments(
            posonlyargs=[],
            args=[],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )

        converted_args.posonlyargs = []
        for _arg in original_args.posonlyargs:
            converted_args.posonlyargs.append(arg(arg=_arg.arg))
        converted_args.args = []
        for _arg in original_args.args:
            converted_args.args.append(arg(arg=_arg.arg))
        converted_args.kwonlyargs = []
        for _arg in original_args.kwonlyargs:
            converted_args.kwonlyargs.append(arg(arg=_arg.arg))
        if original_args.vararg is not None:
            converted_args.vararg = arg(arg=original_args.vararg.arg)
        if original_args.kwarg is not None:
            converted_args.kwarg = arg(arg=original_args.kwarg.arg)

        converted_args.defaults = []
        for default_expr in original_args.defaults:
            converted_args.defaults.append(expr_transf(self.nsp, default_expr))

        converted_args.kw_defaults = []
        for kw_default_expr in original_args.kw_defaults:
            if kw_default_expr is None:
                converted_args.kw_defaults.append(None)
                continue
            converted_args.kw_defaults.append(expr_transf(self.nsp, kw_default_expr))

        self.converted_body = []

    def get_internal_namespace(self):
        return self.internal_nsp

    def _iter_nodes(self) -> typing.Generator[AST, list[expr], None]:
        yield from self._iter_branch(
            self.converted_body,
            self.node.body,
            lambda: self.internal_nsp.return_cnt,
            self.internal_nsp.get_flow_ctrl_expr,
        )

    def get_result(self) -> list[expr]:
        body: list[expr] = []
        body.append(
            NamedExpr(
                target=self.internal_nsp.return_value_expr,
                value=Constant(value=None),
            )
        )

        if self.internal_nsp.zero_arg_super_used:
            # inject free __class__
            body.append(Name(id="__class__", ctx=Load()))

        if self.internal_nsp.flow_ctrl_return_used:
            body.append(
                NamedExpr(
                    target=self.internal_nsp.flow_ctrl_return_expr,
                    value=Constant(value=False),
                )
            )
            # inject flow_ctrl_return to interrupt nodes
            for return_node_body in self.internal_nsp.return_node_bodies:
                return_node_body.append(
                    NamedExpr(
                        target=self.internal_nsp.flow_ctrl_return_expr,
                        value=Constant(value=True),
                    )
                )

        if len(self.internal_nsp.inner_nonlocal_names):
            nonlocal_dict_keys: list[expr] = []
            nonlocal_dict_values: list[expr] = []
            for nonlocal_param in self.internal_nsp.nonlocal_parameters:
                nonlocal_dict_keys.append(Constant(value=nonlocal_param))
                nonlocal_dict_values.append(Name(id=nonlocal_param, ctx=Load()))
            body.append(
                NamedExpr(
                    target=self.internal_nsp.nonlocal_dict_expr,
                    value=Dict(
                        keys=nonlocal_dict_keys,  # type: ignore
                        values=nonlocal_dict_values,
                    ),
                )
            )

        if self.nsp_global.configs.expr_wrapper == "list":
            body.extend(self.converted_body)
        else:
            body.append(self.nsp_global.expr_wraper(self.converted_body))
        body.append(self.internal_nsp.return_value_expr)
        body_expr = utils.list_wrapper(body)

        body_expr = Lambda(
            args=self.converted_args,
            body=Subscript(
                value=body_expr,
                slice=Constant(value=-1),
                ctx=Load(),
            ),
        )
        for dec_expr in reversed(self.node.decorator_list):
            body_expr = Call(
                func=expr_transf(self.nsp, dec_expr),
                args=[body_expr],
                keywords=[],
            )

        if self.internal_nsp.is_method and self.node.name == "__init_subclass__":
            # We need to add a @classmethod for __init_subclass__
            # that's really weird, but really solves problem
            body_expr = Call(
                func=Name(id="classmethod", ctx=Load()),
                args=[body_expr],
                keywords=[],
            )

        return [self.nsp.get_assign(self.node.name, body_expr)]


class PendingReturn(PendingNode[Return]):
    def __init__(self, node: Return, nsp: Namespace, nsp_global: NamespaceGlobal):
        if not isinstance(nsp, NamespaceFunction):
            raise SyntaxError(utils.ast_debug_info(node) + "'return' outside function")

        super().__init__(node, nsp, nsp_global)
        self.nsp: NamespaceFunction

        self.nsp.return_cnt += 1
        for loop in self.nsp.loop_stack:
            loop.break_cnt += 1
            loop.interrupt_cnt += 1

    def get_result(self) -> list[expr]:
        return_list: list[expr] = []
        if self.node.value is not None:
            return_list.append(
                NamedExpr(
                    target=self.nsp.return_value_expr,
                    value=expr_transf(self.nsp, self.node.value),
                )
            )

        for loop in self.nsp.loop_stack:
            if isinstance(loop, PendingWhile):
                return_list.append(
                    NamedExpr(
                        target=loop.flow_ctrl_break_expr,
                        value=Constant(value=True),
                    )
                )
            elif isinstance(loop, PendingFor):
                return_list.append(
                    Call(
                        func=Name(id="setattr", ctx=Load()),
                        args=[
                            loop.flow_ctrl_wrapped_iter_expr,
                            Constant(value="_break"),
                            Constant(value=True),
                        ],
                        keywords=[],
                    )
                )
        for loop in self.nsp.loop_stack:
            loop.interrupt_node_bodies.append(return_list)
        self.nsp.return_node_bodies.append(return_list)
        return [List(elts=return_list, ctx=Load())]


class PendingGlobal(PendingNode[Global]):
    def get_result(self) -> list[expr]:
        return []


class PendingNonlocal(PendingNode[Nonlocal]):
    def get_result(self) -> list[expr]:
        return []


class PendingClassDef(_PendingCompoundStmt[ClassDef]):
    has_internal_namespace = True
    internal_nsp: NamespaceClass
    converted_body: list[expr]

    def __init__(self, node: ClassDef, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)

        for tmp_nsp in self.nsp.inner_nsp:
            if (
                tmp_nsp.symt.get_lineno() == node.lineno
                and tmp_nsp.symt.get_name() == node.name
            ):
                assert isinstance(tmp_nsp, NamespaceClass)
                self.internal_nsp = tmp_nsp
                break
        else:
            raise RuntimeError("Namespace not found")

        self.converted_body = []

    def get_internal_namespace(self) -> Namespace:
        return self.internal_nsp

    def _iter_nodes(self) -> typing.Generator[AST, list[expr], None]:
        yield from self._iter_branch(
            self.converted_body,
            self.node.body,
            lambda: 0,  # class doesn't have any flow control
            utils.never_call,
        )

    def get_result(self) -> list[expr]:
        return_list: list[expr] = []

        class_bases = [expr_transf(self.nsp, _expr) for _expr in self.node.bases]

        metaclass_expr = None
        class_keywords = []
        for _keyword in self.node.keywords:
            if _keyword.arg == "metaclass":
                # filter the metaclass keyword
                metaclass_expr = expr_transf(self.nsp, _keyword.value)
                continue
            class_keywords.append(
                keyword(
                    arg=_keyword.arg,
                    value=expr_transf(self.nsp, _keyword.value),
                )
            )

        if metaclass_expr is None:
            metaclass_expr = Name(id="type", ctx=Load())

        return_list.append(
            self.nsp.get_assign(
                self.node.name,
                Call(
                    func=metaclass_expr,
                    args=[
                        Constant(value=self.node.name),
                        Tuple(elts=class_bases, ctx=Load()),
                        Dict(keys=[], values=[]),
                    ],
                    keywords=class_keywords,
                ),
            )
        )

        class_body: list[expr] = []
        class_body.append(
            NamedExpr(  # one step of injecting the __class__ cell
                target=Name(id="__class__", ctx=Store()),
                value=self.nsp.get_load_name(self.node.name),
            )
        )
        class_body.append(
            NamedExpr(
                target=self.internal_nsp.class_member_dict_expr,
                value=Dict(keys=[], values=[]),
            )
        )
        class_body.extend(self.converted_body)
        class_body.append(self.internal_nsp.class_member_dict_expr)

        loader_name = ol_name(OL_CLASS_LOADER)

        return_list.append(
            NamedExpr(
                target=Name(id=loader_name, ctx=Store()),
                value=Lambda(
                    args=arguments(
                        posonlyargs=[],
                        args=[],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=Subscript(
                        value=List(elts=class_body, ctx=Load()),
                        slice=UnaryOp(op=USub(), operand=Constant(value=1)),
                        ctx=Load(),
                    ),
                ),
            )
        )

        load_class = ListComp(
            elt=Call(
                func=Name(id="setattr", ctx=Load()),
                args=[
                    self.nsp.get_load_name(self.node.name),
                    Name(id="k", ctx=Load()),
                    Name(id="v", ctx=Load()),
                ],
                keywords=[],
            ),
            generators=[
                comprehension(
                    target=Tuple(
                        elts=[Name(id="k", ctx=Store()), Name(id="v", ctx=Store())],
                        ctx=Store(),
                    ),
                    iter=Call(
                        func=Attribute(
                            value=Call(
                                func=Name(id=loader_name, ctx=Load()),
                                args=[],
                                keywords=[],
                            ),
                            attr="items",
                            ctx=Load(),
                        ),
                        args=[],
                        keywords=[],
                    ),
                    ifs=[],
                    is_async=0,
                )
            ],
        )
        return_list.append(load_class)
        return return_list


class PendingImport(PendingNode[Import]):
    def __init__(self, node: Import, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)
        self.nsp_global.use_importlib = True

    def get_result(self) -> list[expr]:
        result = []
        for _alias in self.node.names:
            if _alias.asname is None:
                asname = _alias.name
            else:
                asname = _alias.asname

            result.append(
                self.nsp.get_assign(
                    asname,
                    Call(
                        func=Attribute(
                            value=Name(id="importlib", ctx=Load()),
                            attr="import_module",
                        ),
                        args=[Constant(value=_alias.name)],
                        keywords=[],
                    ),
                )
            )

        return result


class PendingImportFrom(PendingNode[ImportFrom]):
    def __init__(self, node: ImportFrom, nsp: Namespace, nsp_global: NamespaceGlobal):
        super().__init__(node, nsp, nsp_global)

    def get_result(self) -> list[expr]:
        result: list[expr] = []
        tmp_mod_name = ol_name(OL_IMPORT_TMP)

        if self.node.module is None:
            mod_name = ""
        else:
            mod_name = self.node.module

        from_list: list[expr] = []
        for _alias in self.node.names:
            from_list.append(Constant(value=_alias.name))

        import_body = NamedExpr(
            target=Name(id=tmp_mod_name, ctx=Store()),
            value=Call(
                func=Name(id="__import__", ctx=Load()),
                args=[
                    Constant(value=mod_name),
                    Call(func=Name(id="globals", ctx=Load()), args=[], keywords=[]),
                    Call(func=Name(id="locals", ctx=Load()), args=[], keywords=[]),
                    List(elts=from_list, ctx=Load()),
                    Constant(value=self.node.level),
                ],
                keywords=[],
            ),
        )
        result.append(import_body)

        for _alias in self.node.names:
            if _alias.asname is None:
                asname = _alias.name
            else:
                asname = _alias.asname

            if _alias.name == "*":
                raise RuntimeError(
                    "Unable to convert 'from ... import *'"
                )  # pragma: no cover

            result.append(
                self.nsp.get_assign(
                    asname,
                    Attribute(
                        value=Name(id=tmp_mod_name, ctx=Store()),
                        attr=_alias.name,
                    ),
                )
            )

        return result
