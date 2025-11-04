import ast

import pytest

from oneliner.scope_analyzer import analyze_scopes


def test_declare_symbol_by_global_assign():
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


def test_declare_symbol_by_global_ann_assign():
    code = "a: int = 1"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols


def test_declare_symbol_by_global_aug_assign():
    code = "a += 1"
    scope = analyze_scopes(ast.parse(code))
    assert "a" in scope.symbols


def test_declare_symbol_by_global_function_def():
    code = "def func():pass"
    scope = analyze_scopes(ast.parse(code))
    assert "func" in scope.symbols


def test_declare_symbol_by_global_class_def():
    code = "class A():pass"
    scope = analyze_scopes(ast.parse(code))
    assert "A" in scope.symbols


def test_global_in_global_scope():
    code = "global a"
    analyze_scopes(ast.parse(code))  # will not raise an error


def test_nonlocal_in_global_scope():
    code = "nonlocal a"
    with pytest.raises(SyntaxError):
        analyze_scopes(ast.parse(code))
