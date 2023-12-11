class Foo:
    def awa(self):
        print("AwA")


class Foo2(Foo):
    def awa(self):
        # test if zero-argument super() works
        super().awa()
        print("inherit")

    def ovo(self):
        print("OvO")


class Foo3(Foo):
    def awa(self):
        super(Foo3, self).awa()
        print("inherit")


Foo2().awa()
Foo2().ovo()
Foo3().awa()
