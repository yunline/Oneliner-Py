import sys
import unittest

from . import oneliner_test, unparser_test

return_code = 0

result = unittest.main(unparser_test.__name__, exit=False).result
return_code |= not result.wasSuccessful()
result = unittest.main(oneliner_test.__name__, exit=False).result
return_code |= not result.wasSuccessful()

sys.exit(return_code)
