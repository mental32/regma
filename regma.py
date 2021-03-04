import re
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from contextlib import suppress
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    NewType,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

T = TypeVar("T")
U = TypeVar("U")


def _flattened_list(ts: Union[T, List[T]], /) -> Iterator[T]:
    if isinstance(ts, list):
        for t in ts:
            yield from typing.cast("Iterator[T]", _flattened_list(t))
    else:
        yield ts


def _map_exception(
    f: Callable[[], U],
    *,
    default: T,
    catch: Iterable[Type[Exception]],
) -> Union[T, U]:
    try:
        return f()
    except Exception as exc:
        for kind in catch:
            if isinstance(exc, kind):
                return default
        else:
            raise


Match = NewType("Match", str)
ParseResult = Tuple[str, Any]


class RegmaException(Exception):
    """Base class for regma exceptions."""


class RemainingInput(RegmaException):
    """Raised when the input string to `Regex.lex` was partially matches"""


class FailedMatching(RegmaException):
    """Raised when a required rule failed to match correctly."""


class Regma(ABC):
    @abstractmethod
    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        pass

    def __add__(self, o):
        return Seq(rules=[self, o])

    def __radd__(self, o):
        return Seq(rules=[o, self])

    def __or__(self, o):
        return Alt(rules=[self, o])

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


@dataclass
class Literal(Regma):
    pattern: str

    def __call__(self, stream: str, *, ignore_whitespace: bool) -> ParseResult:
        if ignore_whitespace:
            stream = stream.lstrip()

        if stream.startswith(self.pattern):
            length = len(self.pattern)
            stream = stream[length:]

            return (stream, self.pattern)

        raise FailedMatching((stream, self))


@dataclass
class Regex(Regma):
    pattern: Optional[str] = field(default=None)

    def __str__(self) -> str:
        return self.pattern or ""

    def __iter__(self):
        yield self

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        assert self.pattern is not None

        if ignore_whitespace:
            with suppress(FailedMatching):
                result = Whitespace(stream)
                (stream, _) = result

        match = re.match(self.pattern, stream)

        if match is not None:
            length = len(match.group(0))
            return (stream[length:], [Match(match[0])])

        raise FailedMatching((stream, self))

    def lex(self, stream: str, *, ignore_whitespace: bool = False) -> Iterator[str]:
        if type(self) not in (Seq, Regex):
            yield from Seq(rules=[self]).lex(stream, ignore_whitespace=ignore_whitespace)
            return

        for rule in self:
            result = rule(stream, ignore_whitespace=ignore_whitespace)

            (stream, match) = result
            yield from typing.cast("Iterator[Match]", _flattened_list(match))

        if stream:
            raise RemainingInput(stream)


@dataclass
class Ignore(Regex):
    rule: Optional[Regma] = field(default=None)
    discard: Optional[Regma] = field(default=None)

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        assert self.rule is not None
        assert self.discard is not None

        if ignore_whitespace:
            with suppress(FailedMatching):
                result = self.discard(stream)
                (stream, _) = result

        return self.rule(stream, ignore_whitespace=ignore_whitespace)


@dataclass
class Repeating(Regex):
    rule: Optional[Regma] = field(default=None)

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        assert self.rule is not None

        rule = self.rule
        matched = []

        f = lambda stream: _map_exception(
            (lambda: rule(stream, ignore_whitespace=ignore_whitespace)),
            default=None,
            catch=[FailedMatching],
        )

        while (result := f(stream)) is not None:
            (stream, match) = result
            matched.append(match)

        return (stream, matched)


@dataclass
class Atom(Regex):
    rule: Optional[Regma] = field(default=None)

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        assert self.rule is not None

        result = self.rule(stream, ignore_whitespace=ignore_whitespace)

        (stream, _) = result

        matches = typing.cast("Iterable[Union[re.Match, Match]]", _flattened_list(_))

        atom: List[str] = [
            match.group(0) if isinstance(match, re.Match) else match for match in matches
        ]

        return (stream, [Match("".join(atom))])


@dataclass
class Maybe(Regex):
    rule: Optional[Regma] = field(default=None)

    def multiple(self):
        assert self.rule is not None
        return Repeating(rule=self.rule)

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        if self.rule is None:
            return (stream, [])

        return _map_exception(
            (lambda: self.rule(stream, ignore_whitespace=ignore_whitespace)),
            default=(stream, []),
            catch=[FailedMatching],
        )


@dataclass
class RegexGroup(Regex):
    rules: List[Regma] = field(default_factory=list)

    @staticmethod
    def _normalize(seq: List[Any]) -> List[Regma]:
        r = []

        for item in seq:
            if isinstance(item, Regma):
                i = item
            elif isinstance(item, str):
                i = Literal(item)
            else:
                raise TypeError(f"unexpected type to normalize... {item!r}")

            r.append(i)

        return r

    def __post_init__(self):
        self.rules = list(self._normalize(self.rules))

    def __add__(self, o):
        return Seq(rules=[self, o])

    def __or__(self, o):
        return Alt(rules=[self, o])

    def __iter__(self):
        yield from iter(self.rules)


class Alt(RegexGroup):
    def __or__(self, o):
        return Alt(rules=self.rules + [o])

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        for rule in self:
            try:
                result = rule(stream, ignore_whitespace=ignore_whitespace)
            except FailedMatching:
                continue
            else:
                (stream, match) = result
                return (stream, match)

        raise FailedMatching((stream, self))


class Seq(RegexGroup):
    def multiple(self):
        return self + Repeating(rule=self)

    def __call__(self, stream: str, *, ignore_whitespace: bool = False) -> ParseResult:
        matched = []

        for rule in self:
            result = rule(stream, ignore_whitespace=ignore_whitespace)

            (stream, match) = result
            matched.append(typing.cast("Match", match))

        return (stream, matched)


Whitespace = Regex(r"\s+")
