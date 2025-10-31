import ast
import symtable

import oneliner.utils as utils
from oneliner.config import Configs
from oneliner.namespaces import Namespace, generate_nsp
import oneliner.pending_nodes as pending_nodes

class AstToPending:
    _default = object()
    def get(self,item,default=_default) -> pending_nodes.PendingNode:
        if isinstance(item,type):
            return self.get(item.__name__,default)
        if item in pending_nodes.__all__:
            return getattr(pending_nodes,item)
        if "Pending" + item in pending_nodes.__all__:
            return getattr(pending_nodes,"Pending" + item)
        if default is not self._default:
            return default
        raise KeyError(repr(item))
    def __getitem__(self,key) -> pending_nodes.PendingNode:
        return self.get(key)

ast2pending : AstToPending = AstToPending()

def convert(
    ast_root: ast.Module, symtable_root: symtable.SymbolTable, configs: Configs
) -> ast.expr:
    pending_node_stack: list[pending_nodes.PendingNode] = []
    nsp_global = generate_nsp(symtable_root, configs)
    nsp_stack: list[Namespace] = [nsp_global]

    def pending_top() -> pending_nodes.PendingNode:
        """Get the stack top of self.pending_node_stack"""
        return pending_node_stack[-1]

    def get_pending_node(node: ast.AST) -> pending_nodes.PendingNode:
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

    tobe_converted: None | ast.AST = ast_root
    result_nodes = None
    while True:
        assert tobe_converted is not None  # to make type checker happy
        pending_node = get_pending_node(tobe_converted)
        pending_node_stack.append(pending_node)
        if pending_node.has_internal_namespace:
            nsp_stack.append(pending_node.get_internal_namespace())
        tobe_converted = None
        while tobe_converted is None:
            try:
                # try to get unconverted node
                if result_nodes is None:
                    tobe_converted = next(pending_top().iter_node)
                else:
                    tobe_converted = pending_top().iter_node.send(result_nodes)
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
