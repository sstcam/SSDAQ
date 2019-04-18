import math


def get_si_prefix(value: float) -> tuple:
    prefixes = [
        "a",
        "f",
        "p",
        "n",
        "μ",
        "m",
        "",
        "k",
        "M",
        "G",
        "T",
        "P",
        "E",
        "Z",
        "Y",
    ]
    i = int(math.floor(math.log10(value)))
    i = int(i / 3)
    p = math.pow(1000, i)
    s = round(value / p, 2)
    ind = i + 6
    #  if ind<0:
    #     ind = 0
    # if ind>14:
    #     ind=14
    return s, prefixes[ind]
