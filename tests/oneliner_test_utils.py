import io
import os
import unittest

import oneliner


class OnelinerTestError(Exception):
    pass


class OnelinerTestCaseBase(unittest.TestCase):
    original_script: str = ""
    test_case_filename: str

    def print_to_bufffer(self, *args, **kwargs):
        if "file" in kwargs:
            raise TypeError("'file' kwarg used in test case")
        print(*args, file=self.io_buffer, **kwargs)

    def run_code(self, code: str):
        self.reset_runner()
        _globals = {"print": self.print_to_bufffer, "__builtins__": __builtins__}
        _globals.update(self.ext_globals)
        exec(code, _globals)

        return _globals

    def reset_runner(self):
        self.ext_globals = {}
        self.io_buffer = io.StringIO()

    def setUp(self):
        self.reset_runner()

        self.test_case_path = os.path.join(
            os.path.split(__file__)[0], f"test_cases/{self.test_case_filename}"
        )

        with open(self.test_case_path, encoding="utf8") as f:
            self.original_script = f.read()

        self.converted_script = oneliner.convert_code_string(self.original_script)

    def test_if_converted_code_consist_with_original(self):
        self.assertTrue(
            hasattr(self, "converted_script"),
            "Converted script not found.",
        )

        original_result = self.run_code(self.original_script)
        original_buffer = self.io_buffer.getvalue()
        try:
            convertrd_result = self.run_code(self.converted_script)
            convertrd_buffer = self.io_buffer.getvalue()
            self.assertEqual(original_buffer, convertrd_buffer)
            self.compare_test_result(original_result, convertrd_result)
        except Exception as err:
            raise OnelinerTestError(
                f"Test failed.\n\nConverted script:{self.converted_script}"
            ) from err

    def compare_test_result(self, original_result, convertrd_result):
        return True
