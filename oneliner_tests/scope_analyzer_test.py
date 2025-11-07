import ast

import pytest

from oneliner.scope_analyzer import *


def test_assign_symbol_by_assign():
    code = "a = 0"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL

    code = "a, b = 0, 1"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.GLOBAL

    code = "(a, *c, b) = []"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["c"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_ann_assign():
    code = "a: int = 1"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_aug_assign():
    code = "a += 1"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_named_expr():
    code = "(a:=0)"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_function_def():
    code = "def func():pass"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["func"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_class_def():
    code = "class A():pass"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["A"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_import():
    code = "import sys"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["sys"] == SymbolTypeFlags.GLOBAL

    code = "import sys, os, ccb as bcc"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["sys"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["os"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["bcc"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_from_import():
    code = "from random import randint"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["randint"] == SymbolTypeFlags.GLOBAL


    code = "from ... import a, b, c as d"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["d"] == SymbolTypeFlags.GLOBAL


def test_assign_symbol_by_for_loop_target():
    code = """
for i in range(10):
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["i"] == SymbolTypeFlags.GLOBAL

    code = """
for (a, [b, c], d), e in f:
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["c"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["d"] == SymbolTypeFlags.GLOBAL
    assert scope.symbols["e"] == SymbolTypeFlags.GLOBAL

def test_ref_symbol_by_function_decorator():
    code = """
@a
def b():
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_class_decorator():

    code = """
@a
class B:
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_function_arg_default():
    code = """
def a(b, /, c=d, *, e, f = g):
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["d"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["g"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_class_bases_and_kw():
    code = """
class A(B, metaclass=C):
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["B"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["C"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_if():
    code = """
if a:
    print(b)
elif c:
    print(d)
else:
    print(e)
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["c"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["d"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["e"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_while():
    code = """
while a:
    print(b)
else:
    print(c)
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["c"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_for():
    code = """
for i in a:
    print(b)
else:
    print(c)
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["c"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_break_continue_pass_return():
    code = """
for i in range(10):
    if i%2:
        continue
    if i==8:
        break
    if i==114514:
        pass
def a():
    return
"""
    analyze_scopes(ast.parse(code)) # will not raise any error


def test_ref_symbol_by_return():
    code = """
def a():
    return b
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_assign():
    code = "a = b"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_aug_assign():
    code = "a += b"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_ref_symbol_by_ann_assign():
    code = "a:b = c"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["c"] == SymbolTypeFlags.REFERENCED_GLOBAL
    # type alias expression will be ignored
    assert "b" not in scope.symbols


def test_global_in_global_scope():
    code = "global a"
    analyze_scopes(ast.parse(code))  # will not raise an error


def test_nonlocal_in_global_scope():
    code = "nonlocal a"
    with pytest.raises(SyntaxError):
        analyze_scopes(ast.parse(code))


def test_local_in_function_scope():
    code = """
def a():
    b = 0
    b = 1
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["b"] == SymbolTypeFlags.LOCAL


def test_global_in_function_scope():
    code = """
def a():
    global c,c,b
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["c"] == SymbolTypeFlags.GLOBAL
    assert scope.inner_scopes[0].symbols["b"] == SymbolTypeFlags.GLOBAL


def test_global_after_use_or_assign():
    code = """
def a():
    c = 0
    global c
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

    code = """
def a():
    print(c)
    global c
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

def test_declare_global_on_a_parameter():
    code = """
def a(c):
    global c
"""

    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)


def test_nonlocal_after_use_or_assign():
    code = """
def a():
    c = 0
    def b():
        c = 0
        nonlocal c
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

    code = """
def a(): 
    c = 0
    def b():
        print(c)
        nonlocal c
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)


def test_nonlocal_miss():
    code = """
def a():
    def b():
        nonlocal c
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)


def test_nonlocal_repeat():
    code = """
def a():
    c = 0
    def b():
        nonlocal c
        nonlocal c
"""
    analyze_scopes(ast.parse(code))  # no error


def test_nonlocal_and_global_at_the_same_function():
    code = """
def a():
    global b
    nonlocal b
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

    code = """
def q():
    b = 0
    def a():
        nonlocal b
        global b
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

def test_nonlocal_in_nested_function():
    code = """
def a():
    b = 0
    def c():
        def d():
            nonlocal b
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    d_scope = c_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.LOCAL
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert isinstance(d_scope, ScopeFunction)
    assert d_scope.nonlocal_reference_dict["b"] is a_scope


def test_global_symbol_referenced_in_function():
    code = """
def c():
    print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.inner_scopes[0].symbols["print"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_assign_overwrites_symbol_type():
    code = """
def c():
    print(b)
    b = b+1
"""
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["b"] == SymbolTypeFlags.LOCAL


def test_free_symol_analysis():
    code = """
def a():
    b = 0
    def c():
        print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert c_scope.symbols["b"] == SymbolTypeFlags.FREE
    assert isinstance(c_scope, ScopeFunction)
    assert c_scope.nonlocal_reference_dict["b"] is a_scope


def test_nonlocal_symol_analysis():
    code = """
def a():
    b = 1
    def c():
        nonlocal b
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert c_scope.symbols["b"] == SymbolTypeFlags.NONLOCAL_DST
    assert isinstance(c_scope, ScopeFunction)
    assert c_scope.nonlocal_reference_dict["b"] is a_scope


def test_function_parameter():
    code = """
def a(b, /, c, *args, d, e=0, **kw):
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["c"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["args"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["d"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["e"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["kw"] & SymbolTypeFlags.PARAMETER

    code = """
def a(b, /, c, *, d, e=0):
    pass
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["c"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["d"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["e"] & SymbolTypeFlags.PARAMETER


def test_nonlocal_or_free_from_parameter():
    code = """
def a(p1, p2):
    def c():
        nonlocal p1
        print(p2)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    assert c_scope.symbols["p1"] == SymbolTypeFlags.NONLOCAL_DST
    assert c_scope.symbols["p2"] == SymbolTypeFlags.FREE
    assert a_scope.symbols["p1"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["p1"] & SymbolTypeFlags.NONLOCAL_SRC
    assert a_scope.symbols["p2"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["p2"] & SymbolTypeFlags.NONLOCAL_SRC


def test_ref_global_in_lambda():
    code = "lambda:print(a)"
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.inner_scopes[0].symbols["print"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_local_in_lambda():
    code = "lambda:(a:=1)"
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["a"] == SymbolTypeFlags.LOCAL


def test_local_overwrite_in_lambda():
    code = "lambda:[print(a), (a:=1)]"
    scope = analyze_scopes(ast.parse(code))
    assert scope.inner_scopes[0].symbols["a"] == SymbolTypeFlags.LOCAL


def test_free_in_lambda():
    code = """
def a():
    b = 0
    lambda:print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    lambda_scope = a_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert lambda_scope.symbols["b"] == SymbolTypeFlags.FREE


def test_nesting_lambda():
    code = "lambda:lambda:a"
    scope = analyze_scopes(ast.parse(code))
    assert len(scope.inner_scopes) == 1
    assert len(scope.inner_scopes[0].inner_scopes) == 1


def test_parameters_in_lambda():
    code = "lambda b, /, c, *args, d, e=0, **kw:0"
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["c"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["args"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["d"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["e"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["kw"] & SymbolTypeFlags.PARAMETER

    code = "lambda b, /, c, *, d, e=0:0"
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["c"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["d"] & SymbolTypeFlags.PARAMETER
    assert a_scope.symbols["e"] & SymbolTypeFlags.PARAMETER


def test_assign_in_comprehension_in_global():
    code = "[(a:=a+i, c) for i in range(10)]"
    scope = analyze_scopes(ast.parse(code))
    comp_scope = scope.inner_scopes[0]
    assert comp_scope.symbols["a"] == SymbolTypeFlags.COMPREHENSION_ASSIGNMENT
    assert comp_scope.symbols["c"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["i"] == SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp_scope.symbols["range"] == SymbolTypeFlags.COMPREHENSION_REFERENCE


def test_nested_comprehension_reference_target():
    code = "[[(i,j) for j in range(10)] for i in range(10)]"
    scope = analyze_scopes(ast.parse(code))
    comp1_scope = scope.inner_scopes[0]
    comp2_scope = comp1_scope.inner_scopes[0]
    assert comp1_scope.symbols["i"] & SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp2_scope.symbols["j"] & SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp2_scope.symbols["i"] & SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert isinstance(comp2_scope, ScopeComprehensions)
    assert comp2_scope.comprehension_reference_dict["i"] is comp1_scope


def test_nested_comprehension_reference_outer_scope_symbool():
    code = """
def a():
    d = 1
    [[d for j in range(10)] for i in range(10)]
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    comp1_scope = a_scope.inner_scopes[0]
    comp2_scope = comp1_scope.inner_scopes[0]
    assert comp2_scope.symbols["d"] & SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert isinstance(comp2_scope, ScopeComprehensions)
    assert comp2_scope.comprehension_reference_dict["d"] is a_scope

    # is not marked as NONLOCAL_SRC
    assert not a_scope.symbols["d"] & SymbolTypeFlags.NONLOCAL_SRC

def test_assign_to_comprehension_target():
    code = "[i:=1 for i in range(10)]"
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

    code = "[[i:=1 for j in range] for i in range(10)]"
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)


def test_comprehension_assign_overwrite_symbol_type():
    code = """
def a():
    print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] == SymbolTypeFlags.REFERENCED_GLOBAL

    code = """
def a():
    print(b)
    [b:=2 for _ in range(10)]
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] == SymbolTypeFlags.LOCAL


def test_comprehension_assign_creates_new_local_symbole_in_outer_scope():
    code = """
def a():
    [b:=2 for _ in range(10)]
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] == SymbolTypeFlags.LOCAL


def test_comprehension_assign_to_nonlocal():
    code = """
def a():
    b = 1
    def c():
        nonlocal b
        [b:=2 for _ in range(10)]
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    comp_scope = c_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert c_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_DST
    assert comp_scope.symbols["b"] == SymbolTypeFlags.COMPREHENSION_ASSIGNMENT
    

def test_comperhension_assign_inside_class_scope():
    code = """
class A:
    [b:=1 for _ in range(10)]
"""
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)


def test_ref_symbol_in_dict_comprehension():
    code = "{a:b for c in d}"
    scope = analyze_scopes(ast.parse(code))
    comp_scope = scope.inner_scopes[0]
    assert comp_scope.symbols["a"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["b"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["c"] == SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp_scope.symbols["d"] == SymbolTypeFlags.COMPREHENSION_REFERENCE


def test_ref_symbol_in_set_comprehension():
    code = "{a for c in d}"
    scope = analyze_scopes(ast.parse(code))
    comp_scope = scope.inner_scopes[0]
    assert comp_scope.symbols["a"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["c"] == SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp_scope.symbols["d"] == SymbolTypeFlags.COMPREHENSION_REFERENCE


def test_ref_symbol_in_gen_expr():
    code = "(a for c in d)"
    scope = analyze_scopes(ast.parse(code))
    comp_scope = scope.inner_scopes[0]
    assert comp_scope.symbols["a"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["c"] == SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp_scope.symbols["d"] == SymbolTypeFlags.COMPREHENSION_REFERENCE


def test_ref_symbol_in_if_expr_of_comprehension():
    code = "[a for c in d if f]"
    scope = analyze_scopes(ast.parse(code))
    comp_scope = scope.inner_scopes[0]
    assert comp_scope.symbols["f"] == SymbolTypeFlags.COMPREHENSION_REFERENCE


def test_multi_iter_comprehension():
    code = "[a for c in d if f for g in h if i]"
    scope = analyze_scopes(ast.parse(code))
    comp_scope = scope.inner_scopes[0]
    assert comp_scope.symbols["a"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["c"] == SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp_scope.symbols["d"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["f"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["g"] == SymbolTypeFlags.COMPREHENSION_TARGET
    assert comp_scope.symbols["h"] == SymbolTypeFlags.COMPREHENSION_REFERENCE
    assert comp_scope.symbols["i"] == SymbolTypeFlags.COMPREHENSION_REFERENCE


def test_class_assign_local():
    code = """
class A:
    b = 1
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] == SymbolTypeFlags.LOCAL


def test_class_assign_global():
    code = """
class A:
    global b
    b = 1
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["b"] == SymbolTypeFlags.GLOBAL


def test_class_assign_nonlocal():
    code = """
def f():
    b = 0
    class A:
        nonlocal b
        b = 1
"""
    scope = analyze_scopes(ast.parse(code))
    f_scope = scope.inner_scopes[0]
    a_scope = f_scope.inner_scopes[0]
    assert f_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_DST


def test_class_reference_global_symbol():
    code = """
class A:
    print(a)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_class_reference_free():
    code = """
def a():
    b = 0
    class C:
        print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    assert c_scope.symbols["b"] & SymbolTypeFlags.FREE
    assert a_scope.symbols["b"] & SymbolTypeFlags.LOCAL

    # is not marked as NONLOCAL_SRC
    assert not a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC


def test_class_reference_free_in_nested_function_scope():
    code = """
def a():
    b = 0
    def c():
        class D:
            print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    d_scope = c_scope.inner_scopes[0]

    assert d_scope.symbols["b"] & SymbolTypeFlags.FREE
    assert a_scope.symbols["b"] & SymbolTypeFlags.LOCAL

    # is not marked as NONLOCAL_SRC
    assert not a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC


def test_nonlocal_skip_over_class_scope():
    code = """
def a():
    b = 0
    class C:
        b = 1
        def d():
            nonlocal b
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    d_scope = c_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.LOCAL
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert c_scope.symbols["b"] == SymbolTypeFlags.LOCAL
    assert isinstance(d_scope, ScopeFunction)
    assert d_scope.symbols["b"] == SymbolTypeFlags.NONLOCAL_DST
    assert d_scope.nonlocal_reference_dict["b"] is a_scope


def test_free_symbol_skip_over_class_scope():
    code = """
def a():
    b = 0
    class C:
        b = 1
        def d():
            print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    c_scope = a_scope.inner_scopes[0]
    d_scope = c_scope.inner_scopes[0]
    assert a_scope.symbols["b"] & SymbolTypeFlags.LOCAL
    assert a_scope.symbols["b"] & SymbolTypeFlags.NONLOCAL_SRC
    assert c_scope.symbols["b"] == SymbolTypeFlags.LOCAL
    assert isinstance(d_scope, ScopeFunction)
    assert d_scope.symbols["b"] == SymbolTypeFlags.FREE
    assert d_scope.nonlocal_reference_dict["b"] is a_scope


def test_reference_symbol_in_nested_class_scope():
    code = """
def a():
    d = 0
    class B:
        class C:
            print(d)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    b_scope = a_scope.inner_scopes[0]
    c_scope = b_scope.inner_scopes[0]
    assert a_scope.symbols["d"] == SymbolTypeFlags.LOCAL
    assert c_scope.symbols["d"] == SymbolTypeFlags.FREE
    assert c_scope.symbols["print"] == SymbolTypeFlags.REFERENCED_GLOBAL


def test_reference_symbol_multiple_times():
    code = "[print(a), print(a)]"
    scope = analyze_scopes(ast.parse(code))
    assert scope.symbols["print"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert scope.symbols["a"] == SymbolTypeFlags.REFERENCED_GLOBAL

    code = """
def a():
    b = 0
    print(b)
    print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["print"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert a_scope.symbols["b"] == SymbolTypeFlags.LOCAL

    code = """
class A():
    b = 0
    print(b)
    print(b)
"""
    scope = analyze_scopes(ast.parse(code))
    a_scope = scope.inner_scopes[0]
    assert a_scope.symbols["print"] == SymbolTypeFlags.REFERENCED_GLOBAL
    assert a_scope.symbols["b"] == SymbolTypeFlags.LOCAL
