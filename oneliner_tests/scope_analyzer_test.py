import ast

import pytest

from oneliner.scope_analyzer import *


def test_declare_symbol_by_assign():
    code = "a = 0"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols

    code = "a, b = 0, 1"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols
    assert "b" in scope.symbols

    code = "(a, *c, b) = []"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols
    assert "b" in scope.symbols
    assert "c" in scope.symbols


def test_declare_symbol_by_ann_assign():
    code = "a: int = 1"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols


def test_declare_symbol_by_aug_assign():
    code = "a += 1"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols


def test_declare_symbol_by_named_expr():
    code = "(a:=0)"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols


def test_declare_symbol_by_function_def():
    code = "def func():pass"
    scope = analyze_scopes(ast.parse(code))
    assert "func" in scope.symbols


def test_declare_symbol_by_class_def():
    code = "class A():pass"
    scope = analyze_scopes(ast.parse(code))
    assert "A" in scope.symbols


def test_declare_symbol_by_import():
    code = "import sys"
    scope = analyze_scopes(ast.parse(code))
    assert "sys" in scope.symbols

    code = "import sys, os, ccb as bcc"
    scope = analyze_scopes(ast.parse(code))
    assert "sys" in scope.symbols
    assert "os" in scope.symbols
    assert "bcc" in scope.symbols


def test_declare_symbol_by_from_import():
    code = "from random import randint"
    scope = analyze_scopes(ast.parse(code))
    assert "randint" in scope.symbols

    code = "from ... import a, b, c as d"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols
    assert "b" in scope.symbols
    assert "d" in scope.symbols


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


def test_nonlocal_after_use_or_assign():
    code = "def a(): c = 0; global c"
    tree = ast.parse(code)
    with pytest.raises(SyntaxError):
        analyze_scopes(tree)

    code = "def a(): print(c); global c"
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
    assert c_scope.nonlocal_reference_dict["b"].node.name == "a"


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
    assert c_scope.nonlocal_reference_dict["b"].node.name == "a"


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
