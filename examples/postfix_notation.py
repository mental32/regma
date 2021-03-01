from pprint import pprint

from regma import Regex

number = Regex(r"\d+")
postfix_notation = number + (number | r"[\+\-\*\/\^]").repeating()

operators = {
    "+": (lambda a, b: a + b),
    "*": (lambda a, b: a * b),
    "-": (lambda a, b: a - b),
    "/": (lambda a, b: a // b),
    "^": (lambda a, b: a ** b)
}

while (s := input("$ ")): 
    try:
        tokens = list(postfix_notation.lex(s, ignore_whitespace=True))
    except Exception:
        print(f"syntax error: {s!r}")
        continue

    stack = []

    for token in tokens:
        if token.isdigit():
            stack.append(int(token))
            continue

        tos1 = stack.pop()
        tos2 = stack.pop()
        stack.append(operators[token](tos2, tos1))

    print(stack.pop())
