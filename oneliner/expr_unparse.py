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
PERC_NAME = next(enum)
PERC_ATTR = next(enum)
PREC_AWAIT = next(enum)
PREC_POW = next(enum)
PREC_INV = next(enum)
PREC_MULT = next(enum)
PREC_ADD = next(enum)
PREC_SHIFT = next(enum)
PREC_BITAND = next(enum)
PREC_BITXOR = next(enum)
PREC_BITOR = next(enum)
PREC_COMP_ARGS = next(enum)
PREC_COMPARE = next(enum)
PREC_NOT = next(enum)
PREC_AND = next(enum)
PREC_OR = next(enum)
PREC_IFEXP_LEFT = next(enum)
PREC_IFEXP = next(enum)
PREC_FORMAT_EXPR = next(enum)
PREC_LAMBDA = next(enum)
PREC_EXPR = next(enum)
PREC_NAMEDEXPR = next(enum)
PREC_CALLARGS = next(enum)
PREC_GENEXPR = next(enum)
PREC_ONECALLARG = next(enum)
PREC_YIELD = next(enum)
INF = float("inf")


def get_BinOp_precedence(op):
    op_type = type(op)
    if op_type is Pow:
        return PREC_POW
    if op_type in [Mult, MatMult, Div, FloorDiv, Mod]:
        return PREC_MULT
    if op_type in [Add, Sub]:
        return PREC_ADD
    if op_type in [LShift, RShift]:
        return PREC_SHIFT
    if op_type is BitAnd:
        return PREC_BITAND
    if op_type is BitXor:
        return PREC_BITXOR
    if op_type is BitOr:
        return PREC_BITOR
    return INF


def get_BoolOp_precedence(op):
    op_type = type(op)
    if op_type is And:
        return PREC_AND
    if op_type is Or:
        return PREC_OR
    return INF


def get_UnaryOp_precedence(op):
    op_type = type(op)
    if op_type in [UAdd, USub, Invert]:
        return PREC_INV
    if op_type is Not:
        return PREC_NOT
    return INF


ast_prec_map: dict[type[AST] : int] = {
    Constant: PERC_NAME,
    JoinedStr: PERC_NAME,
    FormattedValue: PERC_NAME,
    List: PERC_NAME,
    ListComp: PERC_NAME,
    Tuple: PERC_NAME,
    Dict: PERC_NAME,
    DictComp: PERC_NAME,
    Set: PERC_NAME,
    SetComp: PERC_NAME,
    Name: PERC_NAME,
    Starred: PERC_NAME,
    Attribute: PERC_ATTR,
    Subscript: PERC_ATTR,
    Call: PERC_ATTR,
    Await: PREC_AWAIT,
    Compare: PREC_COMPARE,
    IfExp: PREC_IFEXP,
    Lambda: PREC_LAMBDA,
    keyword: PREC_EXPR,
    Slice: PREC_EXPR,
    NamedExpr: PREC_NAMEDEXPR,
    GeneratorExp: PREC_GENEXPR,
    Yield: PREC_YIELD,
    YieldFrom: PREC_YIELD,
}


def get_precedence(node):
    _type = type(node)
    try:
        return ast_prec_map[type(node)]
    except KeyError:
        pass

    if _type is BinOp:
        return get_BinOp_precedence(node.op)
    if _type is UnaryOp:
        return get_UnaryOp_precedence(node.op)
    if _type is BoolOp:
        return get_BoolOp_precedence(node.op)
    warnings.warn(f"Unknown node precedence of '{type(node).__name__}'", RuntimeWarning)
    return INF


def unparse_generic(node: AST):
    warnings.warn(f"Unknown node type '{type(node).__name__}'", RuntimeWarning)
    return ""
    yield


def unparse_Name(node: Name):
    return node.id
    yield


def get_unescaped_str(string: str, qm: str):
    out = []
    for i in string:
        if i == qm:
            out.append(f"\\{qm}")
        elif ord(i) > 255:
            out.append(i)
        else:
            out.append(ascii(i)[1:-1])
    return "".join(out)


def unparse_Constant(node: Constant, qm):
    if node.value is ...:
        return "..."
    if isinstance(node.value, str):
        value = get_unescaped_str(node.value, qm)
        return f"{qm}{value}{qm}"
    return repr(node.value)
    yield


def _unparse_JoinedStr(node: JoinedStr, qm):
    contents = []
    for v in node.values:
        if isinstance(v, Constant):
            assert isinstance(v.value, str)
            s = get_unescaped_str(v.value, qm)
            s = s.replace("{", "{{").replace("}", "}}")
            contents.append(s)
        elif isinstance(v, FormattedValue):
            contents.append((yield PREC_FORMAT_EXPR, v))
    return "".join(contents)


def unparse_JoinedStr(node: JoinedStr, qm):
    contents = yield from _unparse_JoinedStr(node, qm)
    if sys.version_info < (3, 12) and "\\" in contents:
        raise RuntimeError("Back slash is included in a f-string")
    return f"f{qm}{contents}{qm}"


def unparse_FormattedValue(node: FormattedValue, qm):
    value = yield PREC_FORMAT_EXPR, node.value
    format_spec = ""
    if node.format_spec is not None:
        assert isinstance(node.format_spec, JoinedStr)
        format_spec = yield from _unparse_JoinedStr(node.format_spec, qm)
        format_spec = ":" + format_spec
    return f"{{{value}{format_spec}}}"


def unparse_Starred(node: Starred):
    precedence = PERC_NAME
    value = yield precedence, node.value
    return f"*{value}"
    yield


def unparse_Attribute(node: Attribute):
    precedence = PERC_NAME
    value = yield precedence, node.value
    return f"{value}.{node.attr}"


def unparse_Subscript(node: Subscript):
    precedence = PERC_NAME
    value = yield precedence, node.value
    _slice = yield INF, node.slice
    return f"{value}[{_slice}]"


def unparse_Slice(node: Slice):
    precedence = PREC_EXPR
    upper, lower, step = "", "", ""
    if node.upper is not None:
        upper = yield precedence, node.upper
    if node.lower is not None:
        lower = yield precedence, node.lower
    if node.step is not None:
        step = yield precedence, node.step
    return f"{lower}:{upper}:{step}"


def unparse_keyword(node: keyword):
    precedence = PREC_EXPR
    value = yield precedence, node.value
    if node.arg is None:
        return f"**{value}"
    return f"{node.arg}={value}"


def unparse_Call(node: Call):
    func = yield PERC_ATTR, node.func
    if len(node.args) == 1 and len(node.keywords) == 0:
        _arg = yield PREC_ONECALLARG, node.args[0]
        return f"{func}({_arg})"
    args_list = []
    for _arg in itertools.chain(node.args, node.keywords):
        args_list.append((yield PREC_CALLARGS, _arg))
    _args = ",".join(args_list)
    return f"{func}({_args})"


def unparse_BinOp(node: BinOp):
    precedence = get_BinOp_precedence(node.op)
    op = operator_map[type(node.op)]
    left = yield precedence, node.left
    right = yield precedence, node.right
    return f"{left}{op}{right}"


def unparse_BoolOp(node: BoolOp):
    precedence = get_BoolOp_precedence(node.op)
    op = boolop_map[type(node.op)]
    values = []
    for v in node.values:
        values.append((yield precedence, v))
    return f" {op} ".join(values)


def unparse_UnaryOp(node: UnaryOp):
    precedence = get_UnaryOp_precedence(node.op)
    op = unaryop_map[type(node.op)]
    operand = yield precedence, node.operand
    return f"{op}{operand}"


def unparse_List(node: List):
    elts = []
    for item in node.elts:
        elts.append((yield PREC_CALLARGS, item))
    return f"[{','.join(elts)}]"


def unparse_Set(node: Set):
    elts = []
    for item in node.elts:
        elts.append((yield PREC_CALLARGS, item))
    return f"{{{','.join(elts)}}}"


def unparse_Dict(node: Dict):
    item = []
    for k, v in zip(node.keys, node.values):
        key = yield PREC_EXPR, k
        value = yield PREC_EXPR, v
        item.append(f"{key}:{value}")
    return f"{{{','.join(item)}}}"


def unparse_Tuple(node: Tuple):
    elts = []
    for item in node.elts:
        elts.append((yield PREC_CALLARGS, item))
    if len(elts) == 1:
        return f"({elts[0]},)"
    return f"({','.join(elts)})"


def unparse_Compare(node: Compare):
    ops = (cmpop_map[type(op)] for op in node.ops)
    left = yield PREC_COMP_ARGS, node.left
    comparators = []
    for comparator in node.comparators:
        comparators.append((yield PREC_COMP_ARGS, comparator))
    right = "".join(op + comp for op, comp in zip(ops, comparators))
    return f"{left}{right}"


def unparse_NamedExpr(node: NamedExpr):
    precedence = PREC_NAMEDEXPR
    value = yield precedence, node.value
    return f"{node.target.id}:={value}"


def unparse_Lambda(node: Lambda):
    body = yield PREC_LAMBDA, node.body
    arg_def_list = []

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
            arg_def_list[ind] += f"={yield PREC_EXPR,default}"

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
            kw_list[ind] += f"={yield PREC_EXPR,default}"
    arg_def_list.extend(kw_list)

    # handle kwarg
    if node.args.kwarg:
        arg_def_list.append(f"**{node.args.kwarg.arg}")

    arg_def = ",".join(arg_def_list)
    if arg_def:
        arg_def = " " + arg_def
    return f"lambda{arg_def}:{body}"


def _unparse_comprehensions(generators):
    generator_list = []
    for gen in generators:
        _async = "" if not gen.is_async else "async "
        _iter = yield PREC_EXPR, gen.iter
        target = yield PREC_EXPR, gen.target
        if_list = []
        for test in gen.ifs:
            if_list.append((yield PREC_EXPR, test))
        ifs = " if ".join(if_list)
        if if_list:
            ifs = " if " + ifs
        generator_list.append(f"{_async}for {target} in {_iter}{ifs}")
    return " ".join(generator_list)


def unparse_ListComp(node: ListComp):
    elt = yield PREC_CALLARGS, node.elt
    generators = yield from _unparse_comprehensions(node.generators)
    return f"[{elt} {generators}]"


def unparse_GeneratorExp(node: GeneratorExp):
    elt = yield PREC_CALLARGS, node.elt
    generators = yield from _unparse_comprehensions(node.generators)
    return f"{elt} {generators}"


def unparse_SetComp(node: SetComp):
    elt = yield PREC_CALLARGS, node.elt
    generators = yield from _unparse_comprehensions(node.generators)
    return f"{{{elt} {generators}}}"


def unparse_DictComp(node: DictComp):
    key = yield PREC_EXPR, node.key
    value = yield PREC_EXPR, node.value
    generators = yield from _unparse_comprehensions(node.generators)
    return f"{{{key}:{value} {generators}}}"


def unparse_IfExp(node: IfExp):
    body = yield PREC_IFEXP_LEFT, node.body
    test = yield PREC_IFEXP_LEFT, node.test
    orelse = yield PREC_EXPR, node.orelse
    return f"{body} if {test} else {orelse}"


def unparse_Yield(node: Yield):
    if node.value is None:
        return "yield"
    value = yield PREC_EXPR, node.value
    return f"yield {value}"


def unparse_YieldFrom(node: YieldFrom):
    value = yield PREC_EXPR, node.value
    return f"yield from {value}"


class _Node:
    gen_map: dict[type[AST], typing.Callable] = {
        Name: unparse_Name,
        Call: unparse_Call,
        Constant: unparse_Constant,
        JoinedStr: unparse_JoinedStr,
        FormattedValue: unparse_FormattedValue,
        Starred: unparse_Starred,
        keyword: unparse_keyword,
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
    }

    def __init__(self, outer_precedence, node: AST, outer_str_qm: str):
        self.outer_precedence = outer_precedence
        self.precedence = get_precedence(node)
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


def unparse(node: expr):
    stack: list[_Node] = []
    stack.append(_Node(PREC_EXPR, node, '"'))
    converted: str | None = None
    unconverted: tuple[int, AST] | None = None
    while stack:
        try:
            unconverted = stack[-1].gen.send(converted)
            stack.append(_Node(*unconverted, stack[-1].qm))  # type: ignore
            converted = None
        except StopIteration as err:
            converted = err.value
            inner_node = stack.pop()
            if inner_node.precedence > inner_node.outer_precedence:
                converted = f"({converted})"

    return converted
