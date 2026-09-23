from pathlib import Path
import random

import pytest

from image_worldcup.scanner import ImageEntry
from image_worldcup.tournament import Tournament, allowed_round_sizes


def entries(count: int) -> list[ImageEntry]:
    return [ImageEntry(Path(f"/images/{index}.png")) for index in range(count)]


@pytest.mark.parametrize(
    ("image_count", "expected"),
    [
        (0, ()),
        (1, ()),
        (2, (2,)),
        (3, (2,)),
        (5, (2, 4)),
        (6, (2, 4, 6)),
    ],
)
def test_allowed_round_sizes(image_count: int, expected: tuple[int, ...]) -> None:
    assert allowed_round_sizes(image_count) == expected


@pytest.mark.parametrize(
    ("size", "preliminary_matches", "byes", "base_round"),
    [
        (2, 0, 0, 2),
        (4, 0, 0, 4),
        (6, 2, 2, 4),
        (10, 2, 6, 8),
    ],
)
def test_tournament_bracket_shape(
    size: int,
    preliminary_matches: int,
    byes: int,
    base_round: int,
) -> None:
    tournament = Tournament(entries(size), size, rng=random.Random(7))

    assert tournament.preliminary_match_count == preliminary_matches
    assert tournament.bye_count == byes
    assert tournament.base_round_size == base_round
    if preliminary_matches:
        assert tournament.round_label == f"{size}강 예선"
        assert tournament.round_match_count == preliminary_matches


@pytest.mark.parametrize("size", [2, 4, 6, 10])
def test_tournament_finishes_without_duplicate_matchups(size: int) -> None:
    tournament = Tournament(entries(size), size, rng=random.Random(11))
    seen_by_round: dict[str, set[str]] = {}

    while not tournament.is_finished:
        match = tournament.current_match
        assert match is not None
        assert match.left.key != match.right.key

        round_seen = seen_by_round.setdefault(tournament.round_label, set())
        for participant in match.participants:
            assert participant.key not in round_seen
            round_seen.add(participant.key)
        tournament.select(match.left)

    assert tournament.champion is not None


def test_random_subset_is_reproducible_with_injected_rng() -> None:
    all_images = entries(12)

    first = Tournament(all_images, 6, rng=random.Random(42))
    second = Tournament(all_images, 6, rng=random.Random(42))

    assert [entry.key for entry in first.participants] == [
        entry.key for entry in second.participants
    ]
    assert len(first.participants) == 6
    assert len({entry.key for entry in first.participants}) == 6


def test_only_current_participant_can_win() -> None:
    all_images = entries(4)
    tournament = Tournament(all_images, 4, rng=random.Random(1))
    outsider = ImageEntry(Path("/images/outsider.png"))

    with pytest.raises(ValueError):
        tournament.select(outsider)


def test_history_records_match_round_number_and_winner() -> None:
    tournament = Tournament(entries(4), 4, rng=random.Random(3))
    first_match = tournament.current_match
    assert first_match is not None

    tournament.select(first_match.right)

    assert len(tournament.history) == 1
    result = tournament.history[0]
    assert result.round_label == "4강"
    assert result.match_number == 1
    assert result.match == first_match
    assert result.winner == first_match.right
