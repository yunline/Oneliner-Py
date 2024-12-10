from typing import Any, Literal


class Cfg:
    tp: Any
    default: Any
    value: Any
    docs: str

    def __init__(self, tp, default, docs=""):
        self.tp = tp
        self.default = default
        self.docs = docs
        self.value = default

    def __set__(self, instance, value):
        # todo: verify the value
        self.value = value

    def __get__(self, instance, owner=None):
        return self.value


class Configs:
    unparser = Cfg(
        Literal["ast.unparse", "oneliner"],
        "ast.unparse",
        "Choose the unparser",
    )
    expr_wrapper = Cfg(
        Literal["list", "chain_call"],
        "chain_call",
        "Choose the expr_wrapper",
    )
    config_names = tuple(name for name in locals() if not name.startswith("__"))
