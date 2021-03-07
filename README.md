# Regma
## A Python DSL-like library for creating lexers.

Regma abuses Python operator overloading to provide an API for creating lexers
that feels like as if you were writing a grammar, consider Regma a layer of
syntactic sugar for the builtin regex module.

### Examples

#### Reverse Polish Notation (postfix notation)

```py
from pprint import pprint

from regma import Regex

number = Regex(r"\d+")
operator = Regex(r"[\+\-\*\/\^]")
postfix = number + (number | operator).repeating()

program = "14 6 + 7 ^ 3 * 2 - 4 5 + *"

tokens = list(postfix.lex(program, ignore_whitespace=True))

pprint(tokens)
```

And then `tokens` will be a list of strings that'll be either digits or
operators and you may write your own interpreter on top of that.

But we can get more cheeky than that, by abusing `Regma.map` we have the basis
of action code, code which will run when a rule matches over some tokens.

Here we can use `.map` and a stack to, at parse-time, execute the behaviour of
our program directly:

```py
from regma import Literal, Regex

# our builtin functions
dispatch = {
    "+": (lambda a, b: a + b),
    "-": (lambda a, b: a - b),
    "*": (lambda a, b: a * b),
    "/": (lambda a, b: a / b),
    "^": (lambda a, b: a ** b),
}

stack: List[Any] = [None]

# `list.append` returns None, we are throwing away our number but its fine
# because we have pushed it onto the stack.
number = Regex(r"\d+").map(lambda n: stack.append(int(n[0])))
# Note: you could also write this as: `.map(int).map(stack.append)`

raw_operator = Literal("+") | "-" | "/" | "^" | "*"

program = "14 6 + 7 - 10 * 70 5 5 3 2 + - ^ /"

pop_two = (lambda: [stack.pop(), stack.pop()][::-1])

# `.map`s can be chained to represent a more complex transformation
operator = (
    raw_operator
        .map(lambda op: dispatch[op])      # lookup the associated function
        .map(lambda fun: fun(*pop_two()))  # apply it with the top two numbers on the stack
        .map(stack.append)                 # and push it back onto the stack
)

postfix = number + (number | operator).repeating()

for _ in postfix.lex(program, ignore_whitespace=True):
    continue

top = stack.pop()
print(f"Result: {top=!s}")
```

Voila!

#### Fake Lisp

```py
from pprint import pprint

from regma import Regex

IDENT = Regex(r"[a-zA-Z_-]+")
# IDENT ("." + IDENT)*
attr = (IDENT + ("." + IDENT).repeating()).atom()
# (ATTR | regex "\s" | regex "\d+" )
atom = attr | Regex(r"\s") | Regex(r"\d+")
# "[" ATOM* "]"
lst = "[" + atom.repeating() + "]"
# "(" (ATOM | LIST)* ")"
sexpr = "(" + (atom | lst).repeating() + ")"

tokens = list(sexpr.lex("(reduce-list [ y.z a b c])"))

pprint(tokens)
```
