# type: ignore

# test all types of aug-assign
a = 1
a += 6
print(a)
a -= 2
print(a)
a *= 8
print(a)
a //= 2
print(a)
a /= 2
print(a)
a **= 0.5
print(a)

a = 1
a |= 0xFE
print(a)
a &= 0x08
print(a)
a ^= 0xCC
print(a)
a <<= 2
print(a)
a >>= 4
print(a)


# test aug-assign on subscript/attribute
foo = Foo()
foo.bbb += 1
foo[1:10] += 1

l = [1, 2, 3]
l[:] += [4, 5]
print(l)
