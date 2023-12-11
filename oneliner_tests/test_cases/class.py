class Foo:
    var1 = 0

    def __init__(self):
        print("hello class")
        self._var2 = "hello"

    @classmethod
    def get_foo(cls):
        print("hello classmethod")
        self = cls()
        self.var1 = 1
        return self

    @staticmethod
    def add(a, b):
        print("hello staticmethod")
        return a + b

    @property
    def var2(self):
        print("getting var2")
        return self._var2

    @var2.setter
    def var2(self, v):
        print(f"setting var2 to {v}")
        self._var2 = v


foo = Foo()
print(foo.var1)
foo_clsm = Foo.get_foo()
print(foo_clsm.var1)

print(foo.add(12, 34))

print(foo.var2)
foo.var2 = "hello world"
print(foo.var2)
