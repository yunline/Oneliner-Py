import ast
import sys
import unittest

from oneliner.expr_unparse import expr_unparse


def ast_equivalent(a: ast.AST, b: ast.AST):
    if type(a) is not type(b):
        return False
    for field_name in a._fields:
        a_field = getattr(a, field_name)
        b_field = getattr(b, field_name)
        if type(a_field) is not type(b_field):
            return False
        if isinstance(a_field, ast.AST):
            if not ast_equivalent(a_field, b_field):
                return False
        elif isinstance(a_field, list):
            if len(a_field) != len(b_field):
                return False
            for a_field_item, b_field_item in zip(a_field, b_field):
                if not isinstance(a_field_item, ast.AST):
                    return a_field_item == b_field_item
                if not ast_equivalent(a_field_item, b_field_item):
                    return False
        else:
            return a_field == b_field
    return True


class _TestExprUnparse(unittest.TestCase):
    def assertUnparseConsist(self, code, msg=None):
        original_tree = ast.parse(code, filename="<original>")
        assert isinstance(original_tree.body[0], ast.Expr)
        original_expr = original_tree.body[0].value
        testing_result = expr_unparse(original_expr)
        standard_result = ast.unparse(original_expr)
        testing_tree = ast.parse(testing_result, filename="<expr_unparse>")
        standard_tree = ast.parse(standard_result, filename="<ast.unparse>")

        if not ast_equivalent(testing_tree, original_tree):
            original_dump = ast.dump(original_tree, indent=4)
            testing_dump = ast.dump(testing_tree, indent=4)
            standard_dump = ast.dump(standard_tree, indent=4)
            msg = self._formatMessage(
                msg,
                f"\nexpr_unparse result is different from original\n"
                f"\noriginal:\n{code}\n{original_dump}"
                f"\nast.unparse:\n{standard_result}\n{standard_dump}"
                f"\nexpr_unparse:\n{testing_result}\n{testing_dump}",
            )
            raise self.failureException(msg)
        if not ast_equivalent(standard_tree, original_tree):
            # test the standard lib
            # hopefully we will find cpython bug one day xD
            print(
                f"\nast.unparse result is different from original"
                f"\noriginal: {code}"
                f"\nast.unparse: {standard_result}\n"
                f"\nexpr_unparse: {testing_result}\n"
            )


class TestSingleExprUnparse(_TestExprUnparse):
    def test_Name(self):
        self.assertUnparseConsist("a")

    def test_Constant(self):
        self.assertUnparseConsist("1")
        self.assertUnparseConsist("2.5")
        self.assertUnparseConsist("None")
        self.assertUnparseConsist("...")

    def test_Constant_str(self):
        with self.subTest("Str"):
            self.assertUnparseConsist("'\\u4f60\\u597d\\x77\\x6f\\x72\\x6c\\x64\\x01'")
            self.assertUnparseConsist("'ab\"\\'cd'")
            self.assertUnparseConsist('"ef\'\\"gh"')
            self.assertUnparseConsist('"ji\\\'kl"')
            self.assertUnparseConsist("'mn\\\"op'")
        with self.subTest("JoinedStr"):
            self.assertUnparseConsist("f'hello{world:fmt}hello{0}hello{awa:{q}}}}'")
            if sys.version_info >= (3, 12):
                self.assertUnparseConsist("f'hello{0}fmt\\''")

    def test_List(self):
        self.assertUnparseConsist("[]")
        self.assertUnparseConsist("[a]")
        self.assertUnparseConsist("[a,b,c,d]")

    def test_ListComp(self):
        self.assertUnparseConsist("[a for b in c]")
        self.assertUnparseConsist("[a for b in c if d]")
        self.assertUnparseConsist("[a for b in c if d for e in f]")
        self.assertUnparseConsist("[a async for b in c if d for e in f]")

    def test_GeneratorExp(self):
        self.assertUnparseConsist("(a for b in c)")
        self.assertUnparseConsist("(a for b in c if d)")
        self.assertUnparseConsist("(a for b in c if d for e in f)")
        self.assertUnparseConsist("(a async for b in c if d for e in f)")

    def test_Tuple(self):
        self.assertUnparseConsist("()")
        self.assertUnparseConsist("(a,)")
        self.assertUnparseConsist("(a,b,c)")

    def test_Dict(self):
        self.assertUnparseConsist("{}")
        self.assertUnparseConsist("{a:b}")
        self.assertUnparseConsist("{a:b,c:d}")

    def test_DictComp(self):
        self.assertUnparseConsist("{a:v for b in c}")
        self.assertUnparseConsist("{a:v for b in c if d}")
        self.assertUnparseConsist("{a:v for b in c if d for e in f}")
        self.assertUnparseConsist("{a:v async for b in c if d for e in f}")

    def test_Set(self):
        self.assertUnparseConsist("{a}")
        self.assertUnparseConsist("{a,b,c,d}")

    def test_SetComp(self):
        self.assertUnparseConsist("{a for b in c}")
        self.assertUnparseConsist("{a for b in c if d}")
        self.assertUnparseConsist("{a for b in c if d for e in f}")
        self.assertUnparseConsist("{a async for b in c if d for e in f}")

    def test_Starred(self):
        self.assertUnparseConsist("*a")

    def test_Attr(self):
        self.assertUnparseConsist("a.b")

    def test_Subscript(self):
        self.assertUnparseConsist("a[b]")

    def test_Slice(self):
        self.assertUnparseConsist("a[::]")
        self.assertUnparseConsist("a[b::]")
        self.assertUnparseConsist("a[:c:]")
        self.assertUnparseConsist("a[::d]")
        self.assertUnparseConsist("a[b:c:]")
        self.assertUnparseConsist("a[b::c]")
        self.assertUnparseConsist("a[:b:c]")
        self.assertUnparseConsist("a[b:c:d]")

    def test_Call(self):
        self.assertUnparseConsist("a()")
        self.assertUnparseConsist("a(b)")
        self.assertUnparseConsist("a(b,c)")
        self.assertUnparseConsist("a(b, c=d)")
        self.assertUnparseConsist("a(*b)")
        self.assertUnparseConsist("a(*b, **c)")

    def test_Await(self):
        self.assertUnparseConsist("await a")

    def test_UnaryOp(self):
        self.assertUnparseConsist("~a")
        self.assertUnparseConsist("-a")
        self.assertUnparseConsist("+a")

    def test_BinOp_Pow(self):
        self.assertUnparseConsist("a**b")
        self.assertUnparseConsist("a*b")
        self.assertUnparseConsist("a@b")
        self.assertUnparseConsist("a/b")
        self.assertUnparseConsist("a//b")
        self.assertUnparseConsist("a%b")
        self.assertUnparseConsist("a+b")
        self.assertUnparseConsist("a-b")
        self.assertUnparseConsist("a<<b")
        self.assertUnparseConsist("a>>b")
        self.assertUnparseConsist("a&b")
        self.assertUnparseConsist("a^b")
        self.assertUnparseConsist("a|b")

    def test_BoolOp(self):
        self.assertUnparseConsist("a and b")
        self.assertUnparseConsist("a or b")

    def test_Compare(self):
        self.assertUnparseConsist("a == b")
        self.assertUnparseConsist("a != b")
        self.assertUnparseConsist("a > b")
        self.assertUnparseConsist("a >= b")
        self.assertUnparseConsist("a < b")
        self.assertUnparseConsist("a <= b")
        self.assertUnparseConsist("a is b")
        self.assertUnparseConsist("a is not b")
        self.assertUnparseConsist("a in b")
        self.assertUnparseConsist("a not in b")

    def test_NamedExpr(self):
        self.assertUnparseConsist("(a:=b)")

    def test_Lambda(self):
        self.assertUnparseConsist("lambda:0")
        self.assertUnparseConsist("lambda a:0")
        self.assertUnparseConsist("lambda a,b:0")
        self.assertUnparseConsist("lambda a,b=0:0")
        self.assertUnparseConsist("lambda a,*b,c=0,**d:0")
        self.assertUnparseConsist("lambda a,*b,c=0,**d:0")
        self.assertUnparseConsist("lambda a,b,/,c,d:0")
        self.assertUnparseConsist("lambda a,b=0,c=0,*,d=0:0")

    def test_IfExp(self):
        self.assertUnparseConsist("a if b else c")

    def test_Yield(self):
        self.assertUnparseConsist("yield")
        self.assertUnparseConsist("yield a")

    def test_YieldFrom(self):
        self.assertUnparseConsist("yield from a")


class TestComplexExprUnparse(_TestExprUnparse):
    slots = {
        "List": ["[a,{0},a]"],
        "Tuple": ["(a,{0},a)"],
        "Set": ["{{a,{0},a}}"],
        "Dict": ["{{a:b,{0}:e,c:d}}", "{{a:b,e:{0},c:d}}", "{{a:b,**{0}}}"],
        "JoinedStr": ['f"{{ {0} }} f-string"'],
        "Attr": ["{0}.a"],
        "Subscript": ["a[{0}]", "{0}[a]"],
        "Pow": ["{0}**a", "a**{0}"],
        "Mult": ["{0}*a", "a*{0}"],
        "MatMult": ["{0}@a", "a@{0}"],
        "Div": ["{0}/a", "a/{0}"],
        "FloorDiv": ["{0}//a", "a//{0}"],
        "Mod": ["{0}%a", "a%{0}"],
        "Add": ["{0}+a", "a+{0}"],
        "Sub": ["{0}-a", "a-{0}"],
        "LShift": ["{0}<<a", "a<<{0}"],
        "RShift": ["{0}>>a", "a>>{0}"],
        "BitAnd": ["{0}&a", "a&{0}"],
        "BitXor": ["{0}^a", "a^{0}"],
        "BitOr": ["{0}|a", "a|{0}"],
        "And": ["{0} and q", "q and {0}"],
        "Or": ["{0} or a", "a or {0}"],
        "UAdd": ["+{0}"],
        "USub": ["-{0}"],
        "Invert": ["~{0}"],
        "Not": ["not {0}"],
        "Compare": ["a>{0}", "{0}>a"],
        "IfExp": ["{0} if b else c", "a if {0} else c", "a if b else {0}"],
        "Lambda": ["lambda:{0}", "lambda kw={0}:a"],
        "Call": ["{0}()", "a({0})", "a(kw={0})", "a(*{0})", "a(**{0})", "a(a,b,{0},c)"],
        "Await": ["await {0}"],
        "Yield": ["yield {0}"],
        "YieldFrom": ["yield from {0}"],
        "Slice": ["a[{0}::]"],
        "NamedExpr": ["(a:={0})"],
        "ListComp": ["[{0} for b in c]", "[a for b in {0}]", "[a for b in c if {0}]"],
    }
    plugs = {
        "Const": ["114514", "0.5", "1j", "'x'"],
        "Name": ["a"],
        "List": ["[a]"],
        "Tuple": ["(a,)"],
        "Set": ["{a}"],
        "Dict": ["{a:b}"],
        "Attr": ["a.b"],
        "Pow": ["a**b"],
        "Mult": ["a*b"],
        "MatMult": ["a@b"],
        "Div": ["a/b"],
        "FloorDiv": ["a//b"],
        "Mod": ["a%b"],
        "Add": ["a+b"],
        "Sub": ["a-b"],
        "LShift": ["a<<b"],
        "RShift": ["a>>b"],
        "BitAnd": ["a&b"],
        "BitXor": ["a^b"],
        "BitOr": ["a|b"],
        "And": ["a and b"],
        "Or": ["a or b"],
        "UAdd": ["+a"],
        "USub": ["-a"],
        "Invert": ["~a"],
        "Not": ["not a"],
        "Compare": ["a>b"],
        "IfExp": ["a if b else c"],
        "Lambda": ["lambda:a"],
        "Call": ["print()"],
        "Await": ["await x"],
        "Yield": ["yield", "yield a"],
        "YieldFrom": ["yield from a"],
        "NamedExpr": ["a:=0"],
        "ListComp": ["[a for b in c]"],
        "SetComp": ["{a for b in c}"],
        "GeneratorExp": ["(a for b in c)"],
        "DictComp": ["{a:b for c in d}"],
    }

    # generate test cases
    def gen_complex_test_case(code: str):  # type:ignore
        def test_case(self):
            self.assertUnparseConsist(code)

        return test_case

    for slot_name in slots:
        for slot_ind, slot in enumerate(slots[slot_name]):
            for plug_name in plugs:
                for plug_ind, plug in enumerate(plugs[plug_name]):
                    case_name = f"test_{plug_name}_{plug_ind}_in_{slot_name}_{slot_ind}"
                    locals()[case_name] = gen_complex_test_case(
                        slot.format(f"({plug})")
                    )
    # clean up namespace
    del gen_complex_test_case, slots, plugs
    del slot_name, slot_ind, slot  # type: ignore
    del plug_name, plug_ind, plug  # type: ignore
    del case_name  # type: ignore


if __name__ == "__main__":
    unittest.main()
