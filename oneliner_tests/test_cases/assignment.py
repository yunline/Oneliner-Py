# type: ignore

a = 1
print(a)

b, (c, d, [e, f]) = (1, (2, 3, (4, 5)))
print(b, c, d, e, f)

g = [1, 2, 3, 4]
g[0] = -1
print(g)
g[1:] = [5, 6, 7]
print(g)

h = i, j = (3, 4)
print(h, i, j)

Foo = type("Foo", (), {"a": 0})
foo = Foo()
foo.a = 10
print(foo.a)

ann_only: int
ann_var: int = 0
print(ann_var)

o, *p, q, r = range(8)
print(o, p, q, r)

*s, t, u = range(8)
print(s, t, u)

v, w, *x = range(8)
print(v, w, x)
