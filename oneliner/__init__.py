from oneliner.convert import OnelinerConvertor
from oneliner.expr_unparse import unparse

__all__ = ["OnelinerConvertor", "convert_code_string"]

import ast
import symtable


def convert_code_string(code: str, filename="<string>"):
    ast_root = ast.parse(code, filename, "exec")
    symtable_root = symtable.symtable(code, filename, "exec")
    out = OnelinerConvertor().cvt(ast_root, symtable_root)
    return unparse(out)
