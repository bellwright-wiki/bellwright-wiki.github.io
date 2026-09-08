"""Discover root quests and resolve their ordered subquests."""

from dataclasses import replace
from pathlib import Path

from .cache import QUEST_ROOT, QuestCache
from .model import Quest
from .parser import ObjectIndex, parse_quest

CATEGORY_BLACKLIST = {"BaseBringItemQuest"}


def _categories(assets: Path) -> dict[str, str]:
    """Discover quest categories and build a case-insensitive lookup."""
    root = assets / QUEST_ROOT

    if not root.is_dir():
        return {}

    return {
        path.name.casefold(): path.name
        for path in root.iterdir()
        if path.is_dir() and path.name not in CATEGORY_BLACKLIST
    }


def _category(
    relative: Path,
    categories: dict[str, str],
) -> str | None:
    for part in relative.parts:
        category = categories.get(part.casefold())

        if category:
            return category

    return None


def _sort_quests(
    quests_by_category: dict[str, list[Quest]],
) -> None:
    for quests in quests_by_category.values():
        quests.sort(
            key=lambda quest: (
                tuple(part.casefold() for part in quest.relative_path),
                quest.title.casefold(),
                quest.name.casefold(),
                quest.source.as_posix().casefold(),
            )
        )


def _resolve_path_collisions(
    quests_by_category: dict[str, list[Quest]],
) -> None:
    """Give root quests sharing a source directory distinct tree paths."""
    for quests in quests_by_category.values():
        counts: dict[tuple[str, ...], int] = {}

        for quest in quests:
            counts[quest.relative_path] = (
                counts.get(
                    quest.relative_path,
                    0,
                )
                + 1
            )

        for index, quest in enumerate(quests):
            if counts[quest.relative_path] < 2:
                continue

            quests[index] = replace(
                quest,
                relative_path=quest.relative_path + (quest.source.stem,),
            )


def discover_quests(
    assets: Path,
) -> dict[str, list[Quest]]:
    """Discover quests belonging to all discovered categories."""
    categories = _categories(assets)
    quests_by_category = {category: [] for category in categories.values()}

    cache = QuestCache(assets)
    directory_indexes: dict[Path, ObjectIndex] = cache.directory_indexes()
    quest_titles = cache.quest_titles()

    for path in cache.paths():
        try:
            relative = path.relative_to(assets)
        except ValueError:
            continue

        category = _category(
            relative,
            categories,
        )

        if category is None:
            continue

        quest = parse_quest(
            path=path,
            relative_path=relative,
            category=category,
            objects=cache.objects(path),
            directory_objects=directory_indexes.get(
                path.parent,
                {},
            ),
            quest_titles=quest_titles,
        )

        if quest is not None:
            quests_by_category[category].append(quest)

    _sort_quests(quests_by_category)
    _resolve_path_collisions(quests_by_category)
    _sort_quests(quests_by_category)

    return quests_by_category
