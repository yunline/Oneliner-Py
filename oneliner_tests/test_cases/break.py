print("=== Break from For ===")
for i in range(10):
    if i > 5:
        break
        print("this never prints")
    print(i)

print("=== Break from While ===")
i = 0
while i < 10:
    i = i + 1
    if i > 5:
        break
        print("this never prints")
    print(i)


print("=== Break inside If ===")
for i in range(10):
    if 1:
        if i > 5:
            break
            print("this never prints")
    print(i)

print("=== Break inside If-Else ===")
for i in range(10):
    if 0:
        pass
    else:
        if i > 5:
            break
            print("this never prints")
    print(i)

print("=== Break inside While-Else ===")
for i in range(10):
    while 0:
        pass
    else:
        break
        print("this never prints")
    print("this never prints")

print("=== Break inside For-Else ===")
for i in range(10):
    for _ in []:
        pass
    else:
        break
        print("this never prints")
    print("this never prints")


print("=== Break inside multiple blocks ===")
for i in range(10):
    for _ in []:
        pass
    else:
        while 0:
            pass
        else:
            if 1:
                if i > 5:
                    break
                    print("this never prints")
                print(i, i, i, i)
            print(i, i, i)
        print(i, i)
    print(i)
