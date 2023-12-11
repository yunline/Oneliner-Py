def dec1(func):
    print("dec1 called")
    return func


def dec2(func):
    print("dec2 called")
    return func


@dec2
@dec1
def func():
    pass
