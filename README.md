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
postfix = number + (number | Regex(r"[\+\-\*\/\^]")).repeating()

tokens = list(postfix.lex("14 6 + 7 ^ 3 * 2 - 4 5 + *", ignore_whitespace=True))

pprint(tokens)
```

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
