def func(
    a: int,
    b: int = 1,
    /,
    c: int = 2,
    *args: list[int],
    d: int,
    e: int = 3,
    **kwargs: dict[str, int],
):
    print(a, b, c, d, e)
    print(args)
    print(kwargs)


func(0, 1, 2, 3, 4, 5, 6, 7, 8, d=9, kw1=0, kw2=1)
