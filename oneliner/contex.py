import ast
import typing

import oneliner.utils as utils
from oneliner.config import Configs
from oneliner.namespaces import NamespaceGlobal


class Context:
    nsp_global: NamespaceGlobal
    configs: Configs
    expr_wraper: typing.Callable[[list[ast.expr]], ast.expr]

    def __init__(self, nsp_global: NamespaceGlobal, configs: Configs) -> None:
        self.nsp_global = nsp_global
        self.configs = configs
        self.expr_wraper = utils.get_expr_wrapper(configs)
