import re
import typing
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, NewType, Optional, Tuple


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
        return self.pattern or ""

    def __add__(self, o):
        return Seq(rules=[self, o])

    def __radd__(self, o):
        return Seq(rules=[o, self])

    def __or__(self, o):
        return Alt(rules=[self, o])

    def __iter__(self):
        yield self

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.pattern is not None

        if ignore_whitespace and (result := Whitespace(input)) is not None:
            (input, _) = result

        if (match := re.match(self.pattern, input)) is not None:
            length = len(match.group(0))
            return (input[length:], [Match(match[0])])

        return None

    def multiple(self):
        return Seq(rules=[self, self.repeating()])

    def optional(self):
        return Maybe(rule=self)

    def capture(self):
        return Seq(rules=[self])

    def repeating(self):
        return Repeating(rule=self)

    def atom(self):
        return Atom(rule=self)

    def exactly(self, n: int):
        seq = Seq(rules=[])

        for _ in range(n):
            seq.rules.append(self)

        return self

    def many(self, m: int, n: int):
        seq = Seq(rules=[])

        for _ in range(m):
            seq.rules.append(self)

        for _ in range(n):
            seq.rules.append(self.optional())

        return self

    def lex(self, input: str, *, ignore_whitespace: bool = False) -> Iterator[str]:
        if type(self) not in (Seq, Regex):
            yield from Seq(rules=[self]).lex(input, ignore_whitespace=ignore_whitespace)
            return

        for rule in self:
            result = rule(input, ignore_whitespace=ignore_whitespace)

            if result is None:
                raise Exception(f"Failed to match with {input=!r} ({list(iter(self))=!r})")

            (input, match) = result
            yield from unroll(match)

        if input:
            raise Exception(input)


@dataclass
class Ignore(Regex):
    rule: Optional[Regex] = field(default=None)
    discard: Optional[Regex] = field(default=None)

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.rule is not None
        assert self.discard is not None

        if ignore_whitespace and (result := self.discard(input)) is not None:
            (input, _) = result

        return self.rule(input, ignore_whitespace=ignore_whitespace)


@dataclass
class Repeating(Regex):
    rule: Optional[Regex] = field(default=None)

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.rule is not None

        matched = []

        while (
            result := self.rule(input, ignore_whitespace=ignore_whitespace)
        ) is not None:
            (input, match) = result
            matched.append(typing.cast("Match", match))

        return (input, matched)


@dataclass
class Atom(Regex):
    rule: Optional[Regex] = field(default=None)

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        assert self.rule is not None

        result = self.rule(input, ignore_whitespace=ignore_whitespace)

        if result is None:
            return None

        (input, matches_) = result

        atom = "".join(
            [
                match[0] if isinstance(match, re.Match) else match
                for match in unroll(matches_)
            ]
        )

        return (input, [Match(atom)])


@dataclass
class Maybe(Regex):
    rule: Optional[Regex] = field(default=None)

    def multiple(self):
        assert self.rule is not None
        return Repeating(rule=self.rule)

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        if self.rule is None:
            return (input, [])

        result = self.rule(input, ignore_whitespace=ignore_whitespace)

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
    def __or__(self, o):
        return Alt(rules=self.rules + [o])

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        for rule in self:
            result = rule(input, ignore_whitespace=ignore_whitespace)

            if result is not None:
                (input, match) = result
                return (input, match)

        return None


class Seq(RegexGroup):
    def multiple(self):
        return self + Repeating(rule=self)

    def __call__(
        self, input: str, *, ignore_whitespace: bool = False
    ) -> Optional[Tuple[str, Iterable[Match]]]:
        matched = []

        for rule in self:
            result = rule(input, ignore_whitespace=ignore_whitespace)

            if result is None:
                return None

            (input, match) = result
            matched.append(typing.cast("Match", match))

        return (input, matched)


Whitespace = Regex(r"\s+")
