import re
from abc import ABC
from dataclasses import dataclass, field
from typing import Generic, Iterable, Iterator, List, NewType, Optional, Tuple, TypeVar

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

class Result(ABC, Generic[T, E]):
    """Parsing result type."""


@dataclass
class Err(Result[T, E]):
    e: E


@dataclass
class Ok(Result[T, E]):
    e: T


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

    def __call__(self, input: str) -> Result[Tuple[str, Iterable[Match]], None]:
        assert self.pattern is not None

        if (match := re.match(self.pattern, input)) is not None:
            length = len(match.group(0))
            return Ok((input[length:], [Match(match[0])]))
        else:
            return Err(None)

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

            if isinstance(result, Err):
                raise Exception(f"Failed to match with {input=!r} ({rule=!r})")
            else:
                assert isinstance(result, Ok)
                (input, match) = result.e
                yield from unroll(match)

        if input:
            raise Exception(f"unhandled {input=!r}")



@dataclass
class Repeating(Regex):
    rule: Optional[Regex] = field(default=None)

    def __call__(self, input: str) -> Result[Tuple[str, Iterable[Match]], None]:
        assert self.rule is not None

        matched = []

        while isinstance(result := self.rule(input), Ok):
            assert isinstance(result, Ok)
            (input, match) = result.e
            matched.append(match)

        return Ok((input, matched))


@dataclass
class Atom(Regex):
    rule: Optional[Regex] = field(default=None)

    def __call__(self, input: str) -> Result[Tuple[str, Iterable[Match]], None]:
        assert self.rule is not None

        result = self.rule(input)

        if isinstance(result, Err):
            return result
        else:
            assert isinstance(result, Ok)

        (input, matches_) = result.e

        atom = Match("".join([match[0] if isinstance(match, re.Match) else match for match in unroll(matches_)]))

        return Ok((input, [atom]))


@dataclass
class Maybe(Regex):
    rule: Optional[Regex] = field(default=None)

    def multiple(self):
        assert self.rule is not None
        return Repeating(rule=self.rule)

    def __call__(self, input: str) -> Result[Tuple[str, Iterable[Match]], None]:
        if self.rule is None:
            return Ok((input, []))

        result = self.rule(input)

        if isinstance(result, Err):
            return Ok((input, []))
        else:
            assert isinstance(result, Ok)
            (input, match) = result.e
            return Ok((input, [match]))


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
    def __call__(self, input: str) -> Result[Tuple[str, Iterable[Match]], None]:
        for rule in self:
            result = rule(input)

            if isinstance(result, Ok):
                (input, match) = result.e
                return Ok((input, [match]))

        return Err(None)


class Seq(RegexGroup):
    def multiple(self):
        return self + Repeating(rule=self)

    def __call__(self, input: str) -> Result[Tuple[str, Iterable[Match]], None]:
        matched = []

        for rule in self:
            result = rule(input)

            if isinstance(result, Err):
                return result
            else:
                assert isinstance(result, Ok)
                (input, match) = result.e
                matched.append(match)

        return Ok((input, matched))
