from typing import Any


class Cfg:
    tp: list | type
    default: Any
    value: Any
    docs: str
    name: str

    def __init__(self, tp, default, docs=""):
        self.tp = tp
        self.default = default
        self.docs = docs
        self.value = default

    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        # varify the input value
        if isinstance(self.tp, list):
            if value not in self.tp:
                raise ValueError(
                    f"Invalid value of config '{self.name}', "
                    f"got '{value}', expected {self.tp}"
                )
        else:
            if not isinstance(value, self.tp):
                raise ValueError(f"Invalid value of config '{self.name}'")
        self.value = value

    def __get__(self, instance, owner=None):
        return self.value


class Configs:
    unparser = Cfg(
        ["ast.unparse", "oneliner"],
        "ast.unparse",
        "Choose the unparser",
    )
    expr_wrapper = Cfg(
        ["list", "chain_call"],
        "chain_call",
        "Choose the expr_wrapper",
    )
    if_style = Cfg(
        ["if_expr", "short_circuit"],
        "if_expr",
        "Choose the style of the convertion of 'if' statements",
    )
    config_names = tuple(name for name in locals() if not name.startswith("__"))
