"""
Preset "iter_wrapper"
Used in for loop to handle "break"s
"""

# This is the original code of __ol_iter_wrapper
"""
class __ol_iter_wrapper:
    def __init__(self,it):
        self.it = iter(it)
        self._break = False
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._break:
            next(iter([]))
        else:
            return next(self.it)
"""

# This is the oneliner version __ol_iter_wrapper
"""
(
    __ol_iter_wrapper := type(
        "__ol_iter_wrapper",
        (),
        {
            "__init__": (
                lambda self, it: [
                    setattr(self, "it", iter(it)),
                    setattr(self, "_break", False),
                    None,
                ][-1]
            ),
            "__iter__": (lambda self: self),
            "__next__": (lambda self: next(iter([])) if self._break else next(self.it)),
        },
    )
)
"""

from ast import *

from oneliner.reserved_identifiers import OL_ITER_WRAPPER

iter_wrapper_name = Name(id=OL_ITER_WRAPPER, ctx=Load())
iter_wrapper_body = NamedExpr(
    target=Name(id=OL_ITER_WRAPPER, ctx=Store()),
    value=Call(
        func=Name(id="type", ctx=Load()),
        args=[
            Constant(value=OL_ITER_WRAPPER),
            Tuple(elts=[], ctx=Load()),
            Dict(
                keys=[
                    Constant(value="__init__"),
                    Constant(value="__iter__"),
                    Constant(value="__next__"),
                ],
                values=[
                    Lambda(
                        args=arguments(
                            posonlyargs=[],
                            args=[arg(arg="self"), arg(arg="it")],
                            kwonlyargs=[],
                            kw_defaults=[],
                            defaults=[],
                        ),
                        body=Subscript(
                            value=List(
                                elts=[
                                    Call(
                                        func=Name(id="setattr", ctx=Load()),
                                        args=[
                                            Name(id="self", ctx=Load()),
                                            Constant(value="it"),
                                            Call(
                                                func=Name(id="iter", ctx=Load()),
                                                args=[Name(id="it", ctx=Load())],
                                                keywords=[],
                                            ),
                                        ],
                                        keywords=[],
                                    ),
                                    Call(
                                        func=Name(id="setattr", ctx=Load()),
                                        args=[
                                            Name(id="self", ctx=Load()),
                                            Constant(value="_break"),
                                            Constant(value=False),
                                        ],
                                        keywords=[],
                                    ),
                                    Constant(value=None),
                                ],
                                ctx=Load(),
                            ),
                            slice=UnaryOp(op=USub(), operand=Constant(value=1)),
                            ctx=Load(),
                        ),
                    ),
                    Lambda(
                        args=arguments(
                            posonlyargs=[],
                            args=[arg(arg="self")],
                            kwonlyargs=[],
                            kw_defaults=[],
                            defaults=[],
                        ),
                        body=Name(id="self", ctx=Load()),
                    ),
                    Lambda(
                        args=arguments(
                            posonlyargs=[],
                            args=[arg(arg="self")],
                            kwonlyargs=[],
                            kw_defaults=[],
                            defaults=[],
                        ),
                        body=IfExp(
                            test=Attribute(
                                value=Name(id="self", ctx=Load()),
                                attr="_break",
                                ctx=Load(),
                            ),
                            body=Call(
                                func=Name(id="next", ctx=Load()),
                                args=[
                                    Call(
                                        func=Name(id="iter", ctx=Load()),
                                        args=[List(elts=[], ctx=Load())],
                                        keywords=[],
                                    )
                                ],
                                keywords=[],
                            ),
                            orelse=Call(
                                func=Name(id="next", ctx=Load()),
                                args=[
                                    Attribute(
                                        value=Name(id="self", ctx=Load()),
                                        attr="it",
                                        ctx=Load(),
                                    )
                                ],
                                keywords=[],
                            ),
                        ),
                    ),
                ],
            ),
        ],
        keywords=[],
    ),
)
