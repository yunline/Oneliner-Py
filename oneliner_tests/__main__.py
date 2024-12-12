import unittest

from . import oneliner_test, unparser_test

unittest.main(unparser_test.__name__, exit=False)
unittest.main(oneliner_test.__name__)
