![oneliner-py](https://github.com/yunline/Oneliner-Py/assets/31395137/97ba030b-5d44-4810-9aad-7fed718f18fb)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/yunline/e86b754a309a222ab53215c9d5ff5594/raw/Oneliner-Py_coverage.json)
[![Tests](https://github.com/yunline/Oneliner-Py/actions/workflows/run_test.yml/badge.svg)](https://github.com/yunline/Oneliner-Py/actions/workflows/run_test.yml)

Convert python scripts into **oneliner** expression.  

## Usage
```
python3 -m oneliner [input file] -o [output file]
```

Or use `python3 -m oneliner -h` for help.

## Example
InputFile:
```python
import random
y,h=0,2
msg='hello_world'
while y<h*2:
    for x in range(len(msg)+2):
        print(random.choice('/\\'),end='')
    y+=1
    if y==h:
        print('\n %s '%msg)
    else:
        print('')
```
OutputFile:
```py
[(importlib := __import__('importlib')), (itertools := __import__('itertools')), (random := importlib.import_module('random')), (__ol_assign_qqaleuwbod := (0, 2)), (y := __ol_assign_qqaleuwbod[0]), (h := __ol_assign_qqaleuwbod[1]), (msg := 'hello_world'), [[[print(random.choice('/\\'), end='') for x in range(len(msg) + 2)], y.__iadd__(1) if hasattr(y, '__iadd__') else (y := (y + 1)), print('\n %s ' % msg) if y == h else print('')] for _ in itertools.takewhile(lambda _: y < h * 2, itertools.count())]]
```


## Install
```shell
git clone https://github.com/yunline/Oneliner-Py.git
cd ./Oneliner-Py
python3 -m pip install .
```


