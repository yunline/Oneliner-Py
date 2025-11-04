import unittest

import oneliner_test_utils as test_utils

import oneliner


class TestErrors(unittest.TestCase):
    def test_return_outside_function(self):
        self.assertRaises(
            SyntaxError,
            lambda: oneliner.convert_code_string("return 0"),
        )

    def test_continue_outside_loop(self):
        self.assertRaises(
            SyntaxError,
            lambda: oneliner.convert_code_string("continue"),
        )

    def test_break_outside_loop(self):
        self.assertRaises(
            SyntaxError,
            lambda: oneliner.convert_code_string("break"),
        )

    def test_multiple_starred_expressions(self):
        self.assertRaises(
            SyntaxError,
            lambda: oneliner.convert_code_string("a, *b, c, *d, e = []"),
        )

    def test_unconvertable_node(self):
        """
        Some of statements are not able to be converted as oneliner
        A RuntimeError should raises in this case.
        """
        script = """
try:
    1/0
except ZeroDivisionError:
    pass
"""

        def cvt():
            oneliner.convert_code_string(script)

        self.assertRaises(RuntimeError, cvt)


class TestForLoopCount(test_utils.OnelinerTestCaseBase):
    test_case_filename = "for_loop_count.py"

    def reset_runner(self):
        super().reset_runner()

        class _range:
            """
            Class for testing the iter count in for loop.
            """

            it_cnt = 0

            def __init__(self, *args):
                self.it = iter(range(*args))

            def __iter__(self):
                return self

            def __next__(self):
                self.__class__.it_cnt += 1
                return next(self.it)

        self.ext_globals = {"range": _range}

    def compare_test_result(self, original_result, convertrd_result):
        self.assertEqual(
            original_result["range"].it_cnt, convertrd_result["range"].it_cnt
        )


class TestRecursiveInterrupt(test_utils.OnelinerTestCaseBase):
    test_case_filename = "recursive_interrupt.py"


class TestBreak(test_utils.OnelinerTestCaseBase):
    test_case_filename = "break.py"


class TestIf(test_utils.OnelinerTestCaseBase):
    test_case_filename = "if.py"


class TestAssignment(test_utils.OnelinerTestCaseBase):
    test_case_filename = "assignment.py"


class TestAugmentedAssignment(test_utils.OnelinerTestCaseBase):
    test_case_filename = "aug_assign.py"

    def reset_runner(self):
        super().reset_runner()
        _print = self.print_to_bufffer

        class _Bar:
            def __iadd__(self, v):
                return_value = 999
                _print(f"bar iadd {v}, return {return_value}")
                return return_value

        class _Foo:
            """Class for testing aug-assign on subscript/attribute"""

            def __getitem__(self, slice):
                _print("getitem at", slice)
                return _Bar()

            def __setitem__(self, slice, value):
                _print(f"setitem at {slice}, value: {value}")

            @property
            def bbb(self):
                _print("get bbb")
                return _Bar()

            @bbb.setter
            def bbb(self, value):
                _print("set bbb", value)

        self.ext_globals = {"Foo": _Foo}


class TestNonlocal(test_utils.OnelinerTestCaseBase):
    test_case_filename = "nonlocal.py"


class TestComprehension(test_utils.OnelinerTestCaseBase):
    """
    Test if the namespace of comprehension expr is isolated
    """

    test_case_filename = "comprehension.py"


class TestGlobal(test_utils.OnelinerTestCaseBase):
    test_case_filename = "global.py"


class TestFunctionReturn(test_utils.OnelinerTestCaseBase):
    test_case_filename = "function_return.py"


class TestFunctionDecorator(test_utils.OnelinerTestCaseBase):
    test_case_filename = "function_decorator.py"


class TestFunctionDeclaration(test_utils.OnelinerTestCaseBase):
    test_case_filename = "function_decl.py"


class TestClass(test_utils.OnelinerTestCaseBase):
    test_case_filename = "class.py"


class TestClassInherit(test_utils.OnelinerTestCaseBase):
    test_case_filename = "class_inherit.py"


class TestClassMetaclass(test_utils.OnelinerTestCaseBase):
    test_case_filename = "class_metaclass.py"


class Testimport(test_utils.OnelinerTestCaseBase):
    test_case_filename = "import.py"
