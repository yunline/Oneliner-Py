import itertools
import sys
import typing
import warnings
from ast import *

operator_map: dict[type[operator], str] = {
    Add: "+",
    BitAnd: "&",
    BitOr: "|",
    BitXor: "^",
    Div: "/",
    FloorDiv: "//",
    LShift: "<<",
    Mod: "%",
    Mult: "*",
    MatMult: "@",
    Pow: "**",
    RShift: ">>",
    Sub: "-",
}

boolop_map: dict[type[boolop], str] = {
    And: "and",
    Or: "or",
}

unaryop_map: dict[type[unaryop], str] = {
    UAdd: "+",
    USub: "-",
    Invert: "~",
    Not: "not ",
}

cmpop_map: dict[type[cmpop], str] = {
    Eq: "==",
    Gt: ">",
    GtE: ">=",
    In: " in ",
    Is: " is ",
    IsNot: " is not ",
    Lt: "<",
    LtE: "<=",
    NotEq: "!=",
    NotIn: " not in ",
}
enum = itertools.count()
PREC_NAME = next(enum)

PREC_ATTR = next(enum)
PREC_ATTR_SLOT = next(enum)

PREC_AWAIT_SLOT = next(enum)
PREC_AWAIT = next(enum)

PREC_POW_SLOT_LEFT = next(enum)
PREC_POW = next(enum)
PREC_INV_UADD_USUB = next(enum)
PREC_INV_UADD_USUB_SLOT = next(enum)
PREC_POW_SLOT_RIGHT = next(enum)

PREC_MULT_SLOT_RIGHT = next(enum)
PREC_MULT = next(enum)
PREC_MULT_SLOT_LEFT = next(enum)

PREC_ADD_SLOT_RIGHT = next(enum)
PREC_ADD = next(enum)
PREC_ADD_SLOT_LEFT = next(enum)

PREC_SHIFT_SLOT_RIGHT = next(enum)
PREC_SHIFT = next(enum)
PREC_SHIFT_SLOT_LEFT = next(enum)

PREC_BITAND_SLOT_RIGHT = next(enum)
PREC_BITAND = next(enum)
PREC_BITAND_SLOT_LEFT = next(enum)

PREC_BITXOR_SLOT_RIGHT = next(enum)
PREC_BITXOR = next(enum)
PREC_BITXOR_SLOT_LEFT = next(enum)

PREC_BITOR_SLOT_RIGHT = next(enum)
PREC_BITOR = next(enum)
PREC_BITOR_SLOT_LEFT = next(enum)

PREC_STARRED_SLOT = next(enum)

PREC_COMPARE_SLOT = next(enum)
PREC_COMPARE = next(enum)

PREC_NOT = next(enum)
PREC_NOT_SLOT = next(enum)

PREC_AND_SLOT = next(enum)
PREC_AND = next(enum)

PREC_OR_SLOT = next(enum)
PREC_OR = next(enum)

PREC_COMPREHENSION_SLOT_ITER = next(enum)

PREC_IFEXP_SLOT_LEFT = next(enum)
PREC_IFEXP = next(enum)
PREC_IFEXP_SLOT_RIGHT = next(enum)

PREC_FORMAT_EXPR_SLOT = next(enum)
PREC_LAMBDA = next(enum)
PREC_EXPR_SLOT = next(enum)

PREC_CALL_SLOT_KWARG = next(enum)
PREC_NAMEDEXPR = next(enum)
PREC_CALL_SLOT_ARG = next(enum)
PREC_GENEXPR = next(enum)
PREC_CALL_SLOT_ONLYARG = next(enum)

PREC_YIELD = next(enum)

INF = 1 << 16
prec_t: typing.TypeAlias = int


binop_node_prec_map: dict[type[operator], prec_t] = {
    Pow: PREC_POW,
    Mult: PREC_MULT,
    MatMult: PREC_MULT,
    Div: PREC_MULT,
    FloorDiv: PREC_MULT,
    Mod: PREC_MULT,
    Add: PREC_ADD,
    Sub: PREC_ADD,
    LShift: PREC_SHIFT,
    RShift: PREC_SHIFT,
    BitAnd: PREC_BITAND,
    BitXor: PREC_BITXOR,
    BitOr: PREC_BITOR,
}

boolop_node_prec_map: dict[type[boolop], prec_t] = {
    And: PREC_AND,
    Or: PREC_OR,
}

unaryop_node_prec_map: dict[type[unaryop], prec_t] = {
    UAdd: PREC_INV_UADD_USUB,
    USub: PREC_INV_UADD_USUB,
    Invert: PREC_INV_UADD_USUB,
    Not: PREC_NOT,
}

node_prec_map: dict[type[expr], prec_t] = {
    Constant: PREC_NAME,
    JoinedStr: PREC_NAME,
    FormattedValue: PREC_NAME,
    List: PREC_NAME,
    ListComp: PREC_NAME,
    Tuple: PREC_NAME,
    Dict: PREC_NAME,
    DictComp: PREC_NAME,
    Set: PREC_NAME,
    SetComp: PREC_NAME,
    Name: PREC_NAME,
    Starred: PREC_NAME,
    Attribute: PREC_ATTR,
    Subscript: PREC_ATTR,
    Call: PREC_ATTR,
    Await: PREC_AWAIT,
    Compare: PREC_COMPARE,
    IfExp: PREC_IFEXP,
    Lambda: PREC_LAMBDA,
    Slice: PREC_NAME,
    NamedExpr: PREC_NAMEDEXPR,
    GeneratorExp: PREC_GENEXPR,
    Yield: PREC_YIELD,
    YieldFrom: PREC_YIELD,
}


def get_node_precedence(node: expr) -> prec_t:
    node_prec = INF
    node_prec = node_prec_map.get(type(node), INF)
    if node_prec != INF:
        return node_prec

    if isinstance(node, BinOp):
        node_prec = binop_node_prec_map.get(type(node.op), INF)
    elif isinstance(node, UnaryOp):
        node_prec = unaryop_node_prec_map.get(type(node.op), INF)
    elif isinstance(node, BoolOp):
        node_prec = boolop_node_prec_map.get(type(node.op), INF)
    if node_prec == INF:  # pragma: no cover
        warnings.warn(
            f"Unknown node precedence of '{type(node).__name__}'", RuntimeWarning
        )
    return node_prec


unparse_gen_t: typing.TypeAlias = typing.Generator[tuple[prec_t, expr], str, str]


def unparse_generic(node: expr) -> unparse_gen_t:  # pragma: no cover
    warnings.warn(f"Unknown node type '{type(node).__name__}'", RuntimeWarning)
    return ""
    yield


def unparse_Name(node: Name) -> unparse_gen_t:
    return node.id
    yield


def get_unescaped_str(string: str, qm: str) -> str:
    out = []
    for i in string:
        if i == qm:
            out.append(f"\\{qm}")
        elif ord(i) > 255:
            out.append(i)
        else:
            out.append(ascii(i)[1:-1])
    return "".join(out)


def unparse_Constant(node: Constant, qm: typing.Literal["'", '"']) -> unparse_gen_t:
    if node.value is ...:
        return "..."
    if isinstance(node.value, str):
        value = get_unescaped_str(node.value, qm)
        return f"{qm}{value}{qm}"
    return repr(node.value)
    yield


def _unparse_JoinedStr(node: JoinedStr, qm: typing.Literal["'", '"']) -> unparse_gen_t:
    contents = []
    for v in node.values:
        if isinstance(v, Constant):
            assert isinstance(v.value, str)
            s = get_unescaped_str(v.value, qm)
            s = s.replace("{", "{{").replace("}", "}}")
            contents.append(s)
        elif isinstance(v, FormattedValue):
            contents.append((yield PREC_FORMAT_EXPR_SLOT, v))
    return "".join(contents)


def unparse_JoinedStr(node: JoinedStr, qm: typing.Literal["'", '"']) -> unparse_gen_t:
    contents = yield from _unparse_JoinedStr(node, qm)
    if sys.version_info < (3, 12) and "\\" in contents:  # pragma: no cover
        raise SyntaxError("Back slash is included in a f-string")
    return f"f{qm}{contents}{qm}"


def unparse_FormattedValue(node: FormattedValue, qm) -> unparse_gen_t:
    value = yield PREC_FORMAT_EXPR_SLOT, node.value
    format_spec = ""
    if node.format_spec is not None:
        assert isinstance(node.format_spec, JoinedStr)
        format_spec = yield from _unparse_JoinedStr(node.format_spec, qm)
        format_spec = ":" + format_spec
    if value[0] == "{":
        value = " " + value
    if format_spec and format_spec[-1] == "}":
        format_spec = format_spec + " "
    # f'{{di:ct}:.2f}' (SyntaxError)
    # will be converted as
    # f'{ {di:ct}:.2f}' (Good)
    return "{" + value + format_spec + "}"


def unparse_Starred(node: Starred) -> unparse_gen_t:
    value = yield PREC_STARRED_SLOT, node.value
    return f"*{value}"
    yield


def unparse_Attribute(node: Attribute) -> unparse_gen_t:
    value = yield PREC_ATTR_SLOT, node.value
    if value.isdigit():
        # 0.a is invalid
        # (0).a is valid
        return f"({value}).{node.attr}"
    else:
        return f"{value}.{node.attr}"


def unparse_Subscript(node: Subscript) -> unparse_gen_t:
    value = yield PREC_ATTR_SLOT, node.value
    _slice = yield PREC_EXPR_SLOT, node.slice
    return f"{value}[{_slice}]"


def unparse_Slice(node: Slice) -> unparse_gen_t:
    upper, lower, step = "", "", ""
    if node.upper is not None:
        upper = yield PREC_EXPR_SLOT, node.upper
    if node.lower is not None:
        lower = yield PREC_EXPR_SLOT, node.lower
    if node.step is not None:
        step = yield PREC_EXPR_SLOT, node.step
    return f"{lower}:{upper}:{step}"  # todo: simplify


def unparse_Call(node: Call) -> unparse_gen_t:
    func = yield PREC_ATTR_SLOT, node.func
    if len(node.args) == 1 and len(node.keywords) == 0:
        _arg = yield PREC_CALL_SLOT_ONLYARG, node.args[0]
        return f"{func}({_arg})"
    args_list = []
    for arg_node in node.args:
        args_list.append((yield PREC_CALL_SLOT_ARG, arg_node))
    for kw_node in node.keywords:
        value = (yield PREC_CALL_SLOT_KWARG, kw_node.value)
        if kw_node.arg is None:
            args_list.append(f"**{value}")
        else:
            args_list.append(f"{kw_node.arg}={value}")
    _args = ",".join(args_list)
    return f"{func}({_args})"


def unparse_BinOp(node: BinOp) -> unparse_gen_t:
    op_type = type(node.op)
    if op_type is Pow:
        prec_l = PREC_POW_SLOT_LEFT
        prec_r = PREC_POW_SLOT_RIGHT
    elif op_type in [Mult, MatMult, Div, FloorDiv, Mod]:
        prec_l = PREC_MULT_SLOT_LEFT
        prec_r = PREC_MULT_SLOT_RIGHT
    elif op_type in [Add, Sub]:
        prec_l = PREC_ADD_SLOT_LEFT
        prec_r = PREC_ADD_SLOT_RIGHT
    elif op_type in [LShift, RShift]:
        prec_l = PREC_SHIFT_SLOT_LEFT
        prec_r = PREC_SHIFT_SLOT_RIGHT
    elif op_type is BitAnd:
        prec_l = PREC_BITAND_SLOT_LEFT
        prec_r = PREC_BITAND_SLOT_RIGHT
    elif op_type is BitXor:
        prec_l = PREC_BITXOR_SLOT_LEFT
        prec_r = PREC_BITXOR_SLOT_RIGHT
    elif op_type is BitOr:
        prec_l = PREC_BITOR_SLOT_LEFT
        prec_r = PREC_BITOR_SLOT_RIGHT
    else:  # pragma: no cover
        raise SyntaxError(f"Unknown BinOp type {op_type}")

    op = operator_map[op_type]
    left = yield prec_l, node.left
    right = yield prec_r, node.right
    return f"{left}{op}{right}"


def unparse_BoolOp(node: BoolOp) -> unparse_gen_t:
    if isinstance(node.op, And):
        prec_r = PREC_AND_SLOT
    elif isinstance(node.op, Or):
        prec_r = PREC_OR_SLOT
    else:  # pragma: no cover
        raise SyntaxError(f"Unknown BoolOp type {type(node.op)}")
    op = boolop_map[type(node.op)]
    values = []

    for v in node.values:
        values.append((yield prec_r, v))
    return f" {op} ".join(values)


def unparse_UnaryOp(node: UnaryOp) -> unparse_gen_t:
    if isinstance(node.op, Not):
        precedence = PREC_NOT_SLOT
    elif isinstance(node.op, (Invert, UAdd, USub)):
        precedence = PREC_INV_UADD_USUB_SLOT
    else:  # pragma: no cover
        raise SyntaxError(f"Unknown UnaryOp type {type(node.op)}")
    op = unaryop_map[type(node.op)]
    operand = yield precedence, node.operand
    return f"{op}{operand}"


def unparse_List(node: List) -> unparse_gen_t:
    elts = []
    for item in node.elts:
        elts.append((yield PREC_EXPR_SLOT, item))
    return f"[{','.join(elts)}]"


def unparse_Set(node: Set) -> unparse_gen_t:
    elts = []
    for item in node.elts:
        elts.append((yield PREC_EXPR_SLOT, item))
    return f"{{{','.join(elts)}}}"


def unparse_Dict(node: Dict) -> unparse_gen_t:
    item = []
    for k, v in zip(node.keys, node.values):
        if k is not None:
            value = yield PREC_EXPR_SLOT, v
            key = yield PREC_EXPR_SLOT, k
            item.append(f"{key}:{value}")
        else:
            # **value requires a smaller precedence value
            value = yield PREC_STARRED_SLOT, v
            item.append(f"**{value}")
    return f"{{{','.join(item)}}}"


def unparse_Tuple(node: Tuple) -> unparse_gen_t:
    elts = []
    for item in node.elts:
        elts.append((yield PREC_EXPR_SLOT, item))
    if len(elts) == 1:
        return f"({elts[0]},)"
    return f"({','.join(elts)})"


def unparse_Compare(node: Compare) -> unparse_gen_t:
    ops = (cmpop_map[type(op)] for op in node.ops)
    left = yield PREC_COMPARE_SLOT, node.left
    comparators = []
    for comparator in node.comparators:
        comparators.append((yield PREC_COMPARE_SLOT, comparator))
    right = "".join(op + comp for op, comp in zip(ops, comparators))
    return f"{left}{right}"


def unparse_NamedExpr(node: NamedExpr) -> unparse_gen_t:
    value = yield PREC_EXPR_SLOT, node.value
    return f"{node.target.id}:={value}"


def unparse_Lambda(node: Lambda) -> unparse_gen_t:
    body = yield PREC_EXPR_SLOT, node.body
    arg_def_list = []
    default: expr | None

    # handle posonly args
    for posonly in node.args.posonlyargs:
        arg_def_list.append(posonly.arg)

    # handle args
    for _arg in node.args.args:
        arg_def_list.append(_arg.arg)
    ind = len(arg_def_list)
    for default in reversed(node.args.defaults):
        ind -= 1
        if default is not None:
            arg_def_list[ind] += f"={yield PREC_EXPR_SLOT,default}"

    if node.args.posonlyargs:
        arg_def_list.insert(len(node.args.posonlyargs), "/")

    # handle vararg
    if node.args.vararg:
        arg_def_list.append(f"*{node.args.vararg.arg}")
    elif node.args.kwonlyargs:
        arg_def_list.append("*")

    # handle kwonly args
    kw_list = []
    for kwonly in node.args.kwonlyargs:
        kw_list.append(kwonly.arg)
    for ind, default in enumerate(node.args.kw_defaults):
        if default is not None:
            kw_list[ind] += f"={yield PREC_EXPR_SLOT,default}"
    arg_def_list.extend(kw_list)

    # handle kwarg
    if node.args.kwarg:
        arg_def_list.append(f"**{node.args.kwarg.arg}")

    arg_def = ",".join(arg_def_list)
    if arg_def:
        arg_def = " " + arg_def
    return f"lambda{arg_def}:{body}"


def _unparse_comprehensions(generators: list[comprehension]) -> unparse_gen_t:
    generator_list = []
    for gen in generators:
        _async = "" if not gen.is_async else "async "
        _iter = yield PREC_COMPREHENSION_SLOT_ITER, gen.iter
        target = yield PREC_EXPR_SLOT, gen.target
        if_list = []
        for test in gen.ifs:
            if_list.append((yield PREC_COMPREHENSION_SLOT_ITER, test))
        ifs = " if ".join(if_list)
        if if_list:
            ifs = " if " + ifs
        generator_list.append(f"{_async}for {target} in {_iter}{ifs}")
    return " ".join(generator_list)


def unparse_ListComp(node: ListComp) -> unparse_gen_t:
    elt = yield PREC_EXPR_SLOT, node.elt
    generators = yield from _unparse_comprehensions(node.generators)
    return f"[{elt} {generators}]"


def unparse_GeneratorExp(node: GeneratorExp) -> unparse_gen_t:
    elt = yield PREC_EXPR_SLOT, node.elt
    generators = yield from _unparse_comprehensions(node.generators)
    return f"{elt} {generators}"


def unparse_SetComp(node: SetComp) -> unparse_gen_t:
    elt = yield PREC_EXPR_SLOT, node.elt
    generators = yield from _unparse_comprehensions(node.generators)
    return f"{{{elt} {generators}}}"


def unparse_DictComp(node: DictComp) -> unparse_gen_t:
    key = yield PREC_EXPR_SLOT, node.key
    value = yield PREC_EXPR_SLOT, node.value
    generators = yield from _unparse_comprehensions(node.generators)
    return f"{{{key}:{value} {generators}}}"


def unparse_IfExp(node: IfExp) -> unparse_gen_t:
    body = yield PREC_IFEXP_SLOT_LEFT, node.body
    test = yield PREC_IFEXP_SLOT_LEFT, node.test
    orelse = yield PREC_IFEXP_SLOT_RIGHT, node.orelse
    return f"{body} if {test} else {orelse}"


def unparse_Yield(node: Yield) -> unparse_gen_t:
    if node.value is None:
        return "yield"
    value = yield PREC_EXPR_SLOT, node.value
    return f"yield {value}"


def unparse_YieldFrom(node: YieldFrom) -> unparse_gen_t:
    value = yield PREC_EXPR_SLOT, node.value
    return f"yield from {value}"


def unparse_Await(node: Await) -> unparse_gen_t:
    value = yield PREC_AWAIT_SLOT, node.value
    return f"await {value}"


class _Node:
    gen: unparse_gen_t

    gen_map: dict[type[expr], typing.Callable] = {
        Name: unparse_Name,
        Call: unparse_Call,
        Constant: unparse_Constant,
        JoinedStr: unparse_JoinedStr,
        FormattedValue: unparse_FormattedValue,
        Starred: unparse_Starred,
        BinOp: unparse_BinOp,
        BoolOp: unparse_BoolOp,
        UnaryOp: unparse_UnaryOp,
        List: unparse_List,
        Tuple: unparse_Tuple,
        Set: unparse_Set,
        Dict: unparse_Dict,
        Compare: unparse_Compare,
        Attribute: unparse_Attribute,
        Subscript: unparse_Subscript,
        Slice: unparse_Slice,
        NamedExpr: unparse_NamedExpr,
        Lambda: unparse_Lambda,
        ListComp: unparse_ListComp,
        SetComp: unparse_SetComp,
        DictComp: unparse_DictComp,
        GeneratorExp: unparse_GeneratorExp,
        IfExp: unparse_IfExp,
        Yield: unparse_Yield,
        YieldFrom: unparse_YieldFrom,
        Await: unparse_Await,
    }

    def __init__(self, outer_precedence: prec_t, node: expr, outer_str_qm: str):
        self.outer_precedence = outer_precedence
        self.node_precedence = get_node_precedence(node)
        gen_func = self.gen_map.get(type(node), unparse_generic)

        if gen_func in [unparse_Constant, unparse_JoinedStr]:
            if outer_str_qm == "'":
                self.qm = '"'
            elif outer_str_qm == '"':
                self.qm = "'"
            self.gen = gen_func(node, self.qm)
        elif gen_func is unparse_FormattedValue:
            self.qm = outer_str_qm
            self.gen = gen_func(node, self.qm)
        else:
            self.qm = outer_str_qm
            self.gen = gen_func(node)


"""
Theory

Looking at expression `a*(b*c)`

The `b*c` is inside `a*( )`
`b*c` has a precedence, called "node precedence"
The slot in `a*( )` has a "slot precedence"

If the node precedence value > the slot precedence value
then the inner node should be wrapped with `( )`
Otherwise the `( )` is not needed.

Notice that for some nodes like Mul or Add or IfExpr,
they may have multiple slots with different slot precedence value.
"""


def expr_unparse(node: expr) -> str:
    stack: list[_Node] = []
    stack.append(_Node(PREC_EXPR_SLOT, node, '"'))
    converted: str | None = None
    while stack:
        try:
            # sending None to a just-started generator is equivalent to next(gen)
            slot_prec, unconverted_node = stack[-1].gen.send(converted)  # type: ignore
        except StopIteration as result:
            converted = result.value
            inner_node = stack.pop()
            if inner_node.node_precedence > inner_node.outer_precedence:
                converted = f"({converted})"
        else:
            stack.append(_Node(slot_prec, unconverted_node, stack[-1].qm))
            converted = None

    assert converted is not None
    return converted
