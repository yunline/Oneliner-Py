class Meta(type):
    def __new__(cls, name, bases, dct, **kw):
        x = super().__new__(cls, name, bases, dct, **kw)
        x.attr = 1234
        return x


class Bar:
    def __init_subclass__(cls, hello="") -> None:
        print(f"hello {hello}")


class Foo(Bar, metaclass=Meta, hello="world"):
    pass


print(Foo.attr)
