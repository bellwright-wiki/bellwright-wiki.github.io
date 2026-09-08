"""Render quest documentation to Markdown."""

import json
from pathlib import Path

from ..navigation import breadcrumb_include, navigation_metadata
from .model import Quest, QuestItem, QuestNode, QuestReward, QuestStep


def _format_reward(reward: QuestReward) -> str:
    value = reward.name

    if reward.min_amount is not None and reward.max_amount is not None:
        if reward.min_amount == reward.max_amount:
            amount = str(reward.min_amount)
        else:
            amount = f"{reward.min_amount}–{reward.max_amount}"

        value = f"{value} x {amount}"

    return value


def _format_rewards(
    rewards: tuple[QuestReward, ...],
) -> tuple[list[str], list[str]]:
    guaranteed = []
    random = []

    for reward in rewards:
        value = _format_reward(reward)

        if reward.chance is None:
            guaranteed.append(value)
        else:
            random.append(value)

    return guaranteed, random


def _format_requirements(quest: Quest) -> list[str]:
    requirements = [
        *(f"NPC: {npc}" for npc in quest.required_npcs),
        *(f"Quest: {required_quest}" for required_quest in quest.required_quests),
    ]

    if quest.village_trust_requirement:
        requirements.append(f"Village Trust: {quest.village_trust_requirement}")

    if quest.village_liberation_requirement:
        requirements.append("Village: Liberated")

    return requirements


def _quest_description(quest: Quest) -> str:
    description = f"{quest.title} Quest"
    summary = quest.summary.strip()

    if summary:
        description += f" — {summary}"

    return description


def _category_description(title: str) -> str:
    return f"Quests - {title} Category"


def _quest_rewards(quest: Quest) -> tuple[list[str], list[str]]:
    guaranteed = []

    if quest.village_trust_reward > 0:
        guaranteed.append(f"Village Trust x {quest.village_trust_reward}")

    if quest.village_prosperity_reward > 0:
        guaranteed.append(f"Village Prosperity x {quest.village_prosperity_reward}")

    if quest.money_reward > 0:
        guaranteed.append(f"Money x {quest.money_reward}")

    if quest.renown_reward > 0:
        guaranteed.append(f"Renown x {quest.renown_reward}")

    reward_guaranteed, random = _format_rewards(quest.rewards)
    guaranteed.extend(reward_guaranteed)

    return guaranteed, random


def _write_quest_overview(
    lines: list[str],
    quest: Quest,
) -> None:
    requirements = _format_requirements(quest)

    if not quest.giver and not quest.difficulty and not requirements:
        return

    difficulty = _escape_table_cell(quest.difficulty)
    giver = _escape_table_cell(quest.giver)
    requirements_text = _escape_table_cell("<br>".join(requirements))

    lines.extend(
        [
            "## Quest Overview",
            "",
            "| Difficulty | Giver | Requirements |",
            "|---|---|---|",
            f"| {difficulty} | {giver} | {requirements_text} |",
            "",
        ]
    )


def _write_rewards(
    lines: list[str],
    quest: Quest,
) -> None:
    guaranteed, random = _quest_rewards(quest)

    if not guaranteed and not random:
        return

    lines.extend(
        [
            "### Rewards",
            "",
        ]
    )

    lines.extend(f"- {reward}" for reward in guaranteed)

    if random:
        if guaranteed:
            lines.append("- **Random:**")
        else:
            lines.append("**Random:**")

        lines.extend(f"  - {reward}" for reward in random)

    lines.append("")


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _format_item_list(items: tuple[QuestItem, ...]) -> str:
    values = []

    for item in items:
        if item.min_amount == item.max_amount:
            amount = str(item.min_amount)
        else:
            amount = f"{item.min_amount}-{item.max_amount}"

        values.append(f"{item.name} x {amount}")

    return "<br>".join(values)


def _format_step_name(step: QuestStep) -> str:
    name = step.name

    if step.optional:
        name = f"{name} (Optional)"

    return name


def _write_steps(
    lines: list[str],
    steps: tuple[QuestStep, ...],
) -> None:
    lines.extend(
        [
            "## Steps",
            "",
            "| # | Step | Summary | NPC | Bring | Completion |",
            "|---|---|---|---|---|---|",
        ]
    )

    number = 1
    index = 0

    while index < len(steps):
        step = steps[index]

        if not step.group_next:
            group = [step]
        else:
            group = [step]

            while index + 1 < len(steps) and steps[index].group_next:
                index += 1
                group.append(steps[index])

        for offset, grouped_step in enumerate(group, start=1):
            if len(group) == 1:
                step_number = str(number)
            else:
                step_number = f"{number}.{offset}"

            summary = _escape_table_cell(grouped_step.summary)
            npc = _escape_table_cell(grouped_step.npc)
            items = _escape_table_cell(_format_item_list(grouped_step.items))
            completion = _escape_table_cell(grouped_step.completion_text)

            lines.append(
                f"| {step_number} "
                f"| {_escape_table_cell(_format_step_name(grouped_step))} "
                f"| {summary} "
                f"| {npc} "
                f"| {items} "
                f"| {completion} |"
            )

        number += 1
        index += 1

    lines.append("")


def _write_front_matter(
    lines: list[str],
    title: str,
    description: str | None = None,
    parent: str | None = None,
    parent_url: str | None = None,
    grand_parent: str | None = None,
    grand_parent_url: str | None = None,
) -> None:
    lines.extend(
        [
            "---",
            "layout: default",
            f"title: {json.dumps(title)}",
        ]
    )

    if description:
        lines.append(f"description: {json.dumps(description)}")

    lines.extend(
        [
            *navigation_metadata(
                parent=parent,
                parent_path=parent_url,
                grand_parent=grand_parent,
                grand_parent_path=grand_parent_url,
            ),
            "---",
            "",
            *breadcrumb_include(),
        ]
    )


def _write_quest_page(
    path: Path,
    quest: Quest,
    parent: str,
    parent_url: str | None,
    grand_parent: str | None,
    grand_parent_url: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    _write_front_matter(
        lines,
        quest.title,
        description=_quest_description(quest),
        parent=parent,
        parent_url=parent_url,
        grand_parent=grand_parent,
        grand_parent_url=grand_parent_url,
    )

    lines.extend(
        [
            f"# {quest.title}",
            '{: data-pagefind-meta="title"}',
            "",
        ]
    )

    if quest.summary:
        lines.extend(
            [
                quest.summary,
                "",
            ]
        )

    _write_quest_overview(lines, quest)
    _write_rewards(lines, quest)

    if quest.steps:
        _write_steps(lines, quest.steps)

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _write_page(
    path: Path,
    title: str,
    lines: list[str],
    parent: str | None = None,
    parent_url: str | None = None,
    description: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    content: list[str] = []

    _write_front_matter(
        content,
        title,
        description=description,
        parent=parent,
        parent_url=parent_url,
    )

    content.extend(
        [
            f"# {title}",
            '{: data-pagefind-meta="title"}',
            "",
            *lines,
            "",
        ]
    )

    path.write_text(
        "\n".join(content),
        encoding="utf-8",
    )


def _write_directory(
    node: QuestNode,
    directory: Path,
    category: str,
    category_url: str,
    directory_url: str,
    parent: str | None = None,
    parent_url: str | None = None,
    grand_parent: str | None = None,
    grand_parent_url: str | None = None,
) -> None:
    """Write quest pages while using tree nodes as directories."""
    if node.quest is not None:
        _write_quest_page(
            directory.with_suffix(".md"),
            node.quest,
            parent=parent or category,
            parent_url=parent_url,
            grand_parent=grand_parent,
            grand_parent_url=grand_parent_url,
        )

    if not node.children:
        return

    directory.mkdir(parents=True, exist_ok=True)

    for key, child in sorted(
        node.children.items(),
        key=lambda item: item[1].name.casefold(),
    ):
        if parent is None:
            child_parent = category
            child_parent_url = category_url
            child_grand_parent = None
            child_grand_parent_url = None
        else:
            child_parent = node.name
            child_parent_url = directory_url if node.quest is not None else None
            child_grand_parent = parent
            child_grand_parent_url = parent_url

        _write_directory(
            child,
            directory / key,
            category,
            category_url,
            f"{directory_url}/{key}",
            parent=child_parent,
            parent_url=child_parent_url,
            grand_parent=child_grand_parent,
            grand_parent_url=child_grand_parent_url,
        )


def _write_tree(
    lines: list[str],
    node: QuestNode,
    prefix: str = "",
    indent: int = 0,
) -> None:
    for key, child in sorted(
        node.children.items(),
        key=lambda item: item[1].name.casefold(),
    ):
        padding = "  " * indent

        if child.quest is not None:
            lines.append(f"{padding}- [{child.name}]({prefix}{key})")
            continue

        lines.append(f"{padding}- {child.name}")

        _write_tree(
            lines,
            child,
            f"{prefix}{key}/",
            indent + 1,
        )


def write_category(
    docs: Path,
    category_slug: str,
    tree: QuestNode,
) -> None:
    """Write a quest category."""
    directory = docs / category_slug
    category_url = f"/quests/{category_slug}"

    _write_directory(
        tree,
        directory,
        category=tree.name,
        category_url=category_url,
        directory_url=category_url,
    )

    index_lines: list[str] = []

    _write_tree(
        index_lines,
        tree,
        f"{category_slug}/",
    )

    _write_page(
        docs / f"{category_slug}.md",
        tree.name,
        index_lines,
        description=_category_description(tree.name),
    )
