from pprint import pprint

from regma import Regex

whitespace = Regex(r"\s+")
number = Regex(r"\d+")
postfix_notation = number + whitespace + (number | whitespace | r"[\+\-\*\/\^]").repeating()

operators = {
    "+": (lambda a, b: a + b),
    "*": (lambda a, b: a * b),
    "-": (lambda a, b: a - b),
    "/": (lambda a, b: a // b),
    "^": (lambda a, b: a ** b)
}

while (s := input("$ ")): 
    try:
        tokens = [_ for _ in postfix_notation.lex(s) if _.strip()]
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
