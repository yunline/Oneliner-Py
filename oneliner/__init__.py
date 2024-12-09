from oneliner.convert import OnelinerConvertor
from oneliner.expr_unparse import unparse
from oneliner.config import Configs
import oneliner.utils

__all__ = ["OnelinerConvertor", "convert_code_string"]

import ast
import symtable


def convert_code_string(code: str, filename="<string>", configs:Configs|None=None):
    if configs is None:
        configs = Configs()
    
    # todo: don't change it globally
    if configs.expr_wrapper=="chain_call":
        oneliner.utils._wrap_expr = oneliner.utils.chain_call_wrapper
    else:
        oneliner.utils._wrap_expr = oneliner.utils.list_wrapper

    ast_root = ast.parse(code, filename, "exec")
    symtable_root = symtable.symtable(code, filename, "exec")
    out = OnelinerConvertor().cvt(ast_root, symtable_root)

    if configs.unparser=="oneliner":
        return unparse(out)
    else:
        return ast.unparse(out).replace("\n", "")
