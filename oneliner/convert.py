import ast
import symtable

import oneliner.utils as utils
from oneliner.config import Configs
from oneliner.namespaces import Namespace, generate_nsp
from oneliner.pending_nodes import *

ast2pending: dict[type[ast.AST], type[PendingNode]] = {
    ast.Module: PendingModule,
    ast.Expr: PendingExpr,
    ast.If: PendingIf,
    ast.While: PendingWhile,
    ast.For: PendingFor,
    ast.Break: PendingBreak,
    ast.Continue: PeindingContinue,
    ast.Pass: PendingPass,
    ast.Assign: PendingAssign,
    ast.AnnAssign: PendingAssign,
    ast.AugAssign: PendingAugAssign,
    ast.FunctionDef: PendingFunctionDef,
    ast.Return: PendingReturn,
    ast.Global: PendingGlobal,
    ast.Nonlocal: PendingNonlocal,
    ast.ClassDef: PendingClassDef,
    ast.Import: PendingImport,
    ast.ImportFrom: PendingImportFrom,
}


def convert(
    ast_root: ast.Module, symtable_root: symtable.SymbolTable, configs: Configs
) -> ast.expr:
    pending_node_stack: list[PendingNode] = []
    nsp_global = generate_nsp(symtable_root, configs)
    nsp_stack: list[Namespace] = [nsp_global]

    def pending_top() -> PendingNode:
        """Get the stack top of self.pending_node_stack"""
        return pending_node_stack[-1]

    def get_pending_node(node: ast.AST) -> PendingNode:
        try:
            return ast2pending[type(node)](
                node,
                nsp=nsp_stack[-1],
                nsp_global=nsp_global,
            )
        except KeyError as err:
            raise RuntimeError(
                utils.ast_debug_info(node)  # type: ignore
                + f"Unable to convert node '{type(node).__name__}'"
            ) from err

    unconverted: None | ast.AST = ast_root
    result_nodes = None
    while True:
        assert unconverted is not None  # to make type checker happy
        pending_node = get_pending_node(unconverted)
        pending_node_stack.append(pending_node)
        if pending_node.has_internal_namespace:
            nsp_stack.append(pending_node.get_internal_namespace())
        unconverted = None
        while unconverted is None:
            try:
                # try to get unconverted node
                if result_nodes is None:
                    unconverted = next(pending_top().iter_node)
                else:
                    unconverted = pending_top().iter_node.send(result_nodes)
                    result_nodes = None
            except StopIteration:
                # no more unconverted node, pending node is complete
                complete_node = pending_node_stack.pop()
                if complete_node.has_internal_namespace:
                    nsp_stack.pop()
                result_nodes = complete_node.get_result()

                if len(pending_node_stack) == 0:
                    assert len(nsp_stack) == 1
                    return nsp_global.expr_wraper(result_nodes)
