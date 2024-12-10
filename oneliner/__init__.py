from oneliner.config import Configs
from oneliner.convert import convert
from oneliner.expr_unparse import expr_unparse

__all__ = ["convert_code_string"]

import ast
import symtable


def convert_code_string(code: str, filename="<string>", configs: Configs | None = None):
    if configs is None:
        configs = Configs()

    ast_root = ast.parse(code, filename, "exec")
    symtable_root = symtable.symtable(code, filename, "exec")
    out = convert(ast_root, symtable_root, configs)

    if configs.unparser == "oneliner":
        return expr_unparse(out)
    else:
        return ast.unparse(out).replace("\n", "")
