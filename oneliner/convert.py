import ast
import symtable

import oneliner.utils as utils
from oneliner.namespaces import *
from oneliner.pending_nodes import *


class OnelinerConvertor:
    def __init__(self):
        self.pending_node_stack: list[PendingNode] = []
        self.nsp_stack: list[Namespace] = []

    _pending_map: dict[type[ast.AST], type[PendingNode]] = {
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

    def get_pending_node(self, node: ast.AST) -> PendingNode:
        try:
            return self._pending_map[type(node)](
                node,
                nsp=self.nsp_stack[-1],
                nsp_global=self.nsp_global,
            )
        except KeyError as err:
            raise RuntimeError(
                utils.ast_debug_info(node)
                + f"Unable to convert node '{type(node).__name__}'"
            ) from err

    def pending_top(self) -> PendingNode:
        """Get the stack top of self.pending_node_stack"""
        return self.pending_node_stack[-1]

    def cvt(self, ast_root: ast.Module, symtable_root: symtable.SymbolTable) -> ast.AST:
        self.nsp_global = generate_nsp(symtable_root)
        self.nsp_stack.append(self.nsp_global)
        unconverted = ast_root
        result_nodes = None
        while True:
            pending_node = self.get_pending_node(unconverted)
            self.pending_node_stack.append(pending_node)
            if pending_node.has_internal_namespace:
                self.nsp_stack.append(pending_node.get_internal_namespace())
            unconverted = None
            while unconverted is None:
                try:
                    # try to get unconverted node
                    if result_nodes is None:
                        unconverted = next(self.pending_top().iter_node)
                    else:
                        unconverted = self.pending_top().iter_node.send(result_nodes)
                        result_nodes = None
                except StopIteration:
                    # no more unconverted node, pending node is complete
                    complete_node = self.pending_node_stack.pop()
                    if complete_node.has_internal_namespace:
                        self.nsp_stack.pop()
                    result_nodes = complete_node.get_result()

                    if len(self.pending_node_stack) == 0:
                        assert len(self.nsp_stack) == 1
                        return utils.list_wrapper(result_nodes)
