import re
import typing
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, NewType, Optional, Tuple, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
I = TypeVar("I")
O = TypeVar("O")


def unroll(t):
    if isinstance(t, list):
        for i in t:
            if isinstance(i, list):
                yield from unroll(i)
            else:
                yield i
    else:
        yield t


Match = NewType("Match", str)


@dataclass
class Regex:
    pattern: Optional[str] = field(default=None)

    def __str__(self) -> str:
        # assert self.pattern is not None
        return self.pattern or ""

    def __add__(self, o):
        return Seq(rules=[self, o])

    def __radd__(self, o):
        return Seq(rules=[o, self])

    def __or__(self, o):
        return Alt(rules=[self, o])

    def __iter__(self):
        yield self

    def __call__(self, input: str) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.pattern is not None

        if (match := re.match(self.pattern, input)) is not None:
            length = len(match.group(0))
            return (input[length:], [Match(match[0])])

        return None

    def multiple(self):
        if (s := str(self))[-1] == "?":
            return Regex(f"{s[:-1]}*")

        else:
            return Regex(f"{s!s}+")

    def optional(self):
        return Maybe(rule=self)

    def capture(self):
        return Seq(rules=[self])

    def repeating(self):
        return Repeating(rule=self)

    def atom(self):
        return Atom(rule=self)

    def lex(self, input: str) -> Iterator[str]:
        for rule in self:
            result = rule(input)

            if result is None:
                raise Exception(f"Failed to match with {input=!r} ({rule=!r})")

            (input, match) = result
            yield from unroll(match)

        if input:
            raise Exception(f"unhandled {input=!r}")


@dataclass
class Repeating(Regex):
    rule: Optional[Regex] = field(default=None)

    def __call__(self, input: str) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.rule is not None

        matched = []

        while (result := self.rule(input)) is not None:
            (input, match) = result
            matched.append(typing.cast("Match", match))

        return (input, matched)


@dataclass
class Atom(Regex):
    rule: Optional[Regex] = field(default=None)

    def __call__(self, input: str) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.rule is not None

        result = self.rule(input)

        if result is None:
            return None

        (input, matches_) = result

        atom = Match(
            "".join(
                [
                    match[0] if isinstance(match, re.Match) else match
                    for match in unroll(matches_)
                ]
            )
        )

        return (input, [atom])


@dataclass
class Maybe(Regex):
    rule: Optional[Regex] = field(default=None)

    def multiple(self):
        assert self.rule is not None
        return Repeating(rule=self.rule)

    def __call__(self, input: str) -> Optional[Tuple[str, Iterable[Match]]]:
        if self.rule is None:
            return (input, [])

        result = self.rule(input)

        if result is None:
            return (input, [])

        return result


@dataclass
class RegexGroup(Regex):
    rules: List[Regex] = field(default_factory=list)

    def __post_init__(self):
        self.rules = [Regex(pattern=r) if isinstance(r, str) else r for r in self.rules]

    def __add__(self, o):
        return Seq(rules=[self, o])

    def __or__(self, o):
        return Alt(rules=[self, o])

    def __iter__(self):
        yield from iter(self.rules)


class Alt(RegexGroup):
    def __call__(self, input: str) -> Optional[Tuple[str, Iterable[Match]]]:
        for rule in self:
            result = rule(input)

            if result is not None:
                (input, match) = result
                return (input, match)

        return None


class Seq(RegexGroup):
    def multiple(self):
        return self + Repeating(rule=self)

    def __call__(self, input: str) -> Optional[Tuple[str, Iterable[Match]]]:
        matched = []

        for rule in self:
            result = rule(input)

            if result is None:
                return None

            (input, match) = result
            matched.append(match)

        return (input, matched)
