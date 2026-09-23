from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Protocol, Sequence

from image_worldcup.scanner import ImageEntry


class RandomSource(Protocol):
    def sample(self, population: Sequence[ImageEntry], k: int) -> list[ImageEntry]: ...

    def shuffle(self, x: list[ImageEntry]) -> None: ...


@dataclass(frozen=True, slots=True)
class Match:
    left: ImageEntry
    right: ImageEntry

    @property
    def participants(self) -> tuple[ImageEntry, ImageEntry]:
        return self.left, self.right


@dataclass(frozen=True, slots=True)
class MatchResult:
    round_label: str
    match_number: int
    match: Match
    winner: ImageEntry


def allowed_round_sizes(image_count: int) -> tuple[int, ...]:
    if image_count < 2:
        return ()
    maximum = image_count if image_count % 2 == 0 else image_count - 1
    return tuple(range(2, maximum + 1, 2))


class Tournament:
    def __init__(
        self,
        images: Sequence[ImageEntry],
        size: int,
        *,
        rng: RandomSource | None = None,
    ) -> None:
        if size not in allowed_round_sizes(len(images)):
            raise ValueError("참가 이미지 수는 2 이상인 짝수여야 합니다.")

        keys = [image.key for image in images]
        if len(keys) != len(set(keys)):
            raise ValueError("중복된 이미지 경로는 참가시킬 수 없습니다.")

        self._rng: RandomSource = rng or random.SystemRandom()
        pool = list(images)
        selected = self._rng.sample(pool, size) if size < len(pool) else pool
        self._rng.shuffle(selected)

        self.initial_size = size
        self.participants = tuple(selected)
        self.base_round_size = 1 << math.floor(math.log2(size))
        self.preliminary_match_count = size - self.base_round_size
        self.bye_count = (
            2 * self.base_round_size - size if self.preliminary_match_count else 0
        )

        self._byes: list[ImageEntry] = []
        self._matches: list[Match] = []
        self._match_index = 0
        self._round_winners: list[ImageEntry] = []
        self._is_preliminary = False
        self._round_label = ""
        self._champion: ImageEntry | None = None
        self._history: list[MatchResult] = []

        if self.preliminary_match_count:
            entrant_count = self.preliminary_match_count * 2
            preliminary_entrants = selected[:entrant_count]
            self._byes = selected[entrant_count:]
            self._start_phase(
                preliminary_entrants,
                label=f"{size}강 예선",
                preliminary=True,
            )
        else:
            self._start_standard_round(selected)

    @property
    def current_match(self) -> Match | None:
        if self._champion is not None or not self._matches:
            return None
        return self._matches[self._match_index]

    @property
    def round_label(self) -> str:
        return self._round_label

    @property
    def match_number(self) -> int:
        return self._match_index + 1 if self.current_match else 0

    @property
    def round_match_count(self) -> int:
        return len(self._matches)

    @property
    def champion(self) -> ImageEntry | None:
        return self._champion

    @property
    def is_finished(self) -> bool:
        return self._champion is not None

    @property
    def history(self) -> tuple[MatchResult, ...]:
        return tuple(self._history)

    def select(self, winner: ImageEntry) -> None:
        match = self.current_match
        if match is None:
            raise RuntimeError("진행 중인 경기가 없습니다.")
        if winner not in match.participants:
            raise ValueError("현재 경기의 참가자만 선택할 수 있습니다.")

        self._history.append(
            MatchResult(self._round_label, self._match_index + 1, match, winner)
        )
        self._round_winners.append(winner)
        self._match_index += 1
        if self._match_index < len(self._matches):
            return

        winners = self._round_winners
        if self._is_preliminary:
            next_round = [*self._byes, *winners]
            self._rng.shuffle(next_round)
            self._byes = []
            self._start_standard_round(next_round)
        elif len(winners) == 1:
            self._champion = winners[0]
            self._matches = []
            self._match_index = 0
            self._round_winners = []
        else:
            self._start_standard_round(winners)

    def _start_standard_round(self, participants: list[ImageEntry]) -> None:
        size = len(participants)
        label = "결승" if size == 2 else f"{size}강"
        self._start_phase(participants, label=label, preliminary=False)

    def _start_phase(
        self,
        participants: list[ImageEntry],
        *,
        label: str,
        preliminary: bool,
    ) -> None:
        if len(participants) < 2 or len(participants) % 2:
            raise ValueError("경기 참가자는 2명 이상의 짝수여야 합니다.")
        self._matches = [
            Match(participants[index], participants[index + 1])
            for index in range(0, len(participants), 2)
        ]
        self._match_index = 0
        self._round_winners = []
        self._is_preliminary = preliminary
        self._round_label = label
