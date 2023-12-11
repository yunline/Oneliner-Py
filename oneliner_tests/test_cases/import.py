import sys

print(sys.version)

import os.path as path

print(path.join("./hello", "world.py"))

from os.path import join
from os.path import splitext as sext

print(join("./hello", "world.py"))
print(sext("hello_world.py"))
