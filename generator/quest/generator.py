"""Quest documentation generator orchestration."""

from dataclasses import replace
from pathlib import Path

from .markdown import write_category
from .scanner import discover_quests
from .tree import build_tree

TITLE = "Quests"


def _resolve_required_quests(
    quests_by_category: dict[str, list],
) -> None:
    titles = {
        quest.name.casefold(): quest.title
        for quests in quests_by_category.values()
        for quest in quests
    }

    for quests in quests_by_category.values():
        for index, quest in enumerate(quests):
            quests[index] = replace(
                quest,
                required_quests=tuple(
                    titles.get(name.casefold(), name) for name in quest.required_quests
                ),
            )


def generate(
    assets: Path,
    docs: Path,
    icon_out: Path,
    icon_index: dict,
) -> dict:
    """Generate all discovered quest categories."""
    quests_by_category = discover_quests(assets)
    _resolve_required_quests(quests_by_category)

    print(
        f"Quests indexed: {sum(len(quests) for quests in quests_by_category.values())}"
    )

    quest_docs = docs / "quests"
    quest_docs.mkdir(
        parents=True,
        exist_ok=True,
    )

    pages = []

    for category in quests_by_category:
        slug = category.lower()
        quests = quests_by_category[category]
        tree = build_tree(
            category,
            quests,
        )

        write_category(
            quest_docs,
            slug,
            tree,
        )

        print(f"\tGENERATED quests/{slug}.md ({len(quests)} quests)")

        pages.append(
            {
                "title": category,
                "slug": f"quests/{slug}",
            }
        )

    return {
        "title": TITLE,
        "pages": pages,
    }
