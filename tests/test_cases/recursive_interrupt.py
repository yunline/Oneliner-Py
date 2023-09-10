print("=== For loop ===")

for i in range(20):
    if i % 2:
        continue
    print(i)
    if i % 3:
        continue
    print(i, i)
    if i % 5:
        continue
    print(i, i, i)

print("=== While loop ===")

i = -1
while i < 10:
    i = i + 1
    if i % 2:
        continue
    print(i)
    if i % 3:
        continue
    print(i, i)
    if i % 5:
        continue
    print(i, i, i)

print("=== If ===")

for i in range(20):
    if 1:
        if i % 2:
            continue
        print(i)
        if i % 3:
            continue
        print(i, i)
        if i % 5:
            continue
        print(i, i, i)

print("=== If-Else ===")

for i in range(20):
    if 0:
        pass
    else:
        if i % 2:
            continue
        print(i)
        if i % 3:
            continue
        print(i, i)
        if i % 5:
            continue
        print(i, i, i)

print("=== For-Else ===")

for i in range(20):
    for _ in []:
        pass
    else:
        if i % 2:
            continue
        print(i)
        if i % 3:
            continue
        print(i, i)
        if i % 5:
            continue
        print(i, i, i)

print("=== While-Else ===")

for i in range(20):
    while 0:
        pass
    else:
        if i % 2:
            continue
        print(i)
        if i % 3:
            continue
        print(i, i)
        if i % 5:
            continue
        print(i, i, i)
