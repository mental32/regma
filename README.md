# Regma
## A Python DSL-like library for creating lexers.

Regma abuses Python operator overloading to provide an API for creating lexers
that feels like as if you were writing a regular grammar.

### Examples

#### Reverse Polish Notation (postfix notation)

```py
from regma import Regex

whitespace = Regex(r"\s+")
number = Regex(r"\d+")
postfix = number + whitespace + (number | whitespace | r"[\+\-\*\/\^]").repeating()

from pprint import pprint

tokens = list(postfix.lex("14 6 + 7 ^ 3 * 2 - 4 5 + *"))

pprint(tokens)
```

#### Fake Lisp

```py
from regma import Regex

IDENT = Regex(r"[a-zA-Z_-]+")

# IDENT ("." + IDENT)*
attr = (IDENT + (r"\." + IDENT).repeating()).atom()

# (ATTR | regex "\s" | regex "\d+" )
atom = attr | r"\s" | r"\d+"

# "[" ATOM* "]"
lst = r"\[" + atom.repeating() + r"\]"

# "(" (ATOM | LIST)* ")"
sexpr = r"\(" + (atom | lst).repeating() + r"\)"

from pprint import pprint

tokens = list(sexpr.lex("(reduce-list [ y.z a b c])"))

pprint(tokens)
```
