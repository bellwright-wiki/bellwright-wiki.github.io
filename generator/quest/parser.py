"""Parse exported Unreal objects into quest models."""

from pathlib import Path

from .model import Quest, QuestItem, QuestReward, QuestStep

ObjectIndex = dict[str, tuple[Path, list[dict]]]


def _object_name(obj: dict) -> str:
    value = obj.get("Name")
    return value.strip() if isinstance(value, str) else ""


def _usable_object_name(value: str) -> str:
    if not value or value.startswith("Default__"):
        return ""

    if value.endswith("_C"):
        value = value[:-2]

    return value.strip()


def _quest_object(objects: list[dict]) -> dict | None:
    for obj in objects:
        value = obj.get("Type")

        if isinstance(value, str) and "quest" in value.casefold():
            return obj

    return None


def _text(value) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in (
            "SourceString",
            "LocalizedString",
            "StringTableEntry",
            "Value",
            "Text",
        ):
            result = _text(value.get(key))

            if result:
                return result

    return ""


def _description(obj: dict) -> str:
    properties = obj.get("Properties")

    if not isinstance(properties, dict):
        return ""

    for key, value in properties.items():
        if key.casefold().endswith("taskdescription"):
            result = _text(value)

            if result:
                return result

    return _text(properties.get("Description"))


def _class_name(value) -> str:
    if not isinstance(value, dict):
        return ""

    object_name = value.get("ObjectName")

    if not isinstance(object_name, str):
        return ""

    start = object_name.find("'")
    end = object_name.rfind("'")

    if start == -1 or end <= start:
        return ""

    return _usable_object_name(object_name[start + 1 : end])


def _npc_name(value) -> str:
    if isinstance(value, dict) and "TalkClass" in value:
        value = value.get("TalkClass")

    name = _class_name(value)

    if name.endswith("Talk"):
        name = name[:-4]

    return " ".join(_split_words(name)).strip()


def _int(value, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            pass

    return default


def _float(value, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass

    return default


def _items(obj: dict) -> tuple[QuestItem, ...]:
    properties = obj.get("Properties")
    values = properties.get("Items") if isinstance(properties, dict) else None

    if not isinstance(values, list):
        return ()

    result = []

    for value in values:
        if not isinstance(value, dict):
            continue

        item_name = _class_name(value.get("ItemClass"))

        if not item_name:
            continue

        min_amount = _int(value.get("MinAmount"))
        max_amount = _int(value.get("MaxAmount"), min_amount)

        result.append(
            QuestItem(
                name=item_name,
                min_amount=min_amount,
                max_amount=max_amount,
            )
        )

    return tuple(result)


def _reward_name(value) -> str:
    name = _class_name(value)

    if not name:
        return ""

    result = []

    for word in _split_words(name):
        if word and word[-1].isdigit():
            split_at = len(word)

            while split_at > 0 and word[split_at - 1].isdigit():
                split_at -= 1

            if split_at > 0:
                result.extend(
                    [
                        word[:split_at],
                        word[split_at:],
                    ]
                )
                continue

        result.append(word)

    return " ".join(result)


def _table_reward(table: dict) -> QuestReward | None:
    name = _reward_name(table.get("Table"))

    if not name:
        return None

    min_multiplier = table.get("MinQuantityMultiplier")
    max_multiplier = table.get("MaxQuantityMultiplier")

    if min_multiplier is None and max_multiplier is None:
        min_amount = None
        max_amount = None
    else:
        min_amount = _int(min_multiplier, 1)
        max_amount = _int(max_multiplier, min_amount)

    run_chance = _float(table.get("RunChance"), 1.0)
    per_iteration_chance = _float(
        table.get("PerIterationRunChance"),
        run_chance,
    )

    min_iterations = _int(table.get("MinIterations"), 1)
    max_iterations = _int(
        table.get("MaxIterations"),
        min_iterations,
    )

    per_roll = min_iterations != max_iterations

    return QuestReward(
        name=name,
        min_amount=min_amount,
        max_amount=max_amount,
        chance=per_iteration_chance if per_roll else run_chance,
        per_roll=per_roll,
    )


def _rewards(obj: dict) -> tuple[QuestReward, ...]:
    properties = obj.get("Properties")
    item_reward = properties.get("ItemReward") if isinstance(properties, dict) else None

    if not isinstance(item_reward, dict):
        return ()

    rewards = []

    outputs = item_reward.get("Outputs")

    if isinstance(outputs, list):
        for output in outputs:
            if not isinstance(output, dict):
                continue

            name = _reward_name(output.get("ItemClass"))

            if not name:
                continue

            rewards.append(
                QuestReward(
                    name=name,
                    min_amount=_int(output.get("MinQuantity")),
                    max_amount=_int(output.get("MaxQuantity")),
                )
            )

    tables = item_reward.get("Tables")

    if isinstance(tables, list):
        for table in tables:
            if not isinstance(table, dict):
                continue

            reward = _table_reward(table)

            if reward is not None:
                rewards.append(reward)

    return tuple(rewards)


def _subquests(obj: dict) -> list[tuple[str, str, bool]]:
    properties = obj.get("Properties")
    values = properties.get("Subquests") if isinstance(properties, dict) else None

    if not isinstance(values, list):
        return []

    result = []

    for value in values:
        if not isinstance(value, dict):
            continue

        name = _class_name(value.get("QuestClass"))

        if not name:
            continue

        quest_type = value.get("Type")

        if not isinstance(quest_type, str):
            quest_type = ""

        result.append(
            (
                name,
                quest_type,
                bool(value.get("bGroupNext", False)),
            )
        )

    return result


def _split_words(value: str) -> list[str]:
    words = []
    word = ""

    for index, char in enumerate(value):
        previous = value[index - 1] if index else ""
        following = value[index + 1] if index + 1 < len(value) else ""

        boundary = (
            char == "_"
            or (word and char.isupper() and previous.islower())
            or (word and char.isupper() and previous.isupper() and following.islower())
        )

        if boundary:
            if word:
                words.append(word)
                word = ""

            if char == "_":
                continue

        word += char

    if word:
        words.append(word)

    return words


def _fallback_step_title(
    quest_name: str,
    step_name: str,
) -> str:
    name = step_name

    if name.startswith(f"{quest_name}_"):
        name = name[len(quest_name) + 1 :]
    elif name.startswith(quest_name):
        name = name[len(quest_name) :]

    return " ".join(_split_words(name.lstrip("_"))).strip()


def _step_title(
    quest_name: str,
    quest_title: str,
    step_name: str,
    step_object: dict,
) -> str:
    properties = step_object.get("Properties")
    title = _text(properties.get("Title")) if isinstance(properties, dict) else ""

    if title and title.casefold() != quest_title.casefold():
        return title

    return _fallback_step_title(
        quest_name,
        step_name,
    )


def _step_npc(step_object: dict) -> str:
    properties = step_object.get("Properties")

    if not isinstance(properties, dict):
        return ""

    npc = _npc_name(properties.get("NpcRef"))

    if npc:
        return npc

    return _npc_name(properties.get("DefaultQuestGiverRef"))


def _required_npcs(obj: dict) -> tuple[str, ...]:
    properties = obj.get("Properties")
    values = (
        properties.get("RequiredNpcsForQuestToBeVisible")
        if isinstance(properties, dict)
        else None
    )

    if not isinstance(values, list):
        return ()

    result = []

    for value in values:
        npc = _npc_name(value)

        if npc and npc not in result:
            result.append(npc)

    return tuple(result)


def _resolve_steps(
    quest_name: str,
    quest_title: str,
    subquests: list[tuple[str, str, bool]],
    objects: ObjectIndex,
) -> tuple[QuestStep, ...]:
    steps = []

    for name, quest_type, group_next in subquests:
        entry = objects.get(name)

        if entry is None:
            continue

        source, step_objects = entry
        step_object = _quest_object(step_objects)

        if step_object is None:
            continue

        properties = step_object.get("Properties")

        if not isinstance(properties, dict):
            properties = {}

        steps.append(
            QuestStep(
                name=_step_title(
                    quest_name,
                    quest_title,
                    name,
                    step_object,
                ),
                source=source,
                summary=_description(step_object),
                completion_text=_text(properties.get("CompletionText")),
                type=quest_type,
                optional="optional" in quest_type.casefold(),
                group_next=group_next,
                items=_items(step_object),
                npc=_step_npc(step_object),
            )
        )

    return tuple(steps)


def _quest_npcs(
    quest_object: dict,
    steps: tuple[QuestStep, ...],
    giver: str,
) -> tuple[str, ...]:
    result = []

    for npc in _required_npcs(quest_object):
        if npc and npc.casefold() != giver.casefold():
            if npc not in result:
                result.append(npc)

    for step in steps:
        if (
            step.npc
            and step.npc.casefold() != giver.casefold()
            and step.npc not in result
        ):
            result.append(step.npc)

    return tuple(result)


def parse_quest(
    path: Path,
    relative_path: Path,
    category: str,
    objects: list[dict],
    directory_objects: ObjectIndex,
) -> Quest | None:
    """Parse a root quest from loaded Unreal objects."""
    quest_object = _quest_object(objects)

    if quest_object is None:
        return None

    properties = quest_object.get("Properties")

    if not isinstance(properties, dict):
        return None

    if not isinstance(properties.get("Subquests"), list):
        return None

    name = _usable_object_name(_object_name(quest_object)) or path.stem
    title = _text(properties.get("Title")) or name

    steps = _resolve_steps(
        name,
        title,
        _subquests(quest_object),
        directory_objects,
    )

    giver = _npc_name(properties.get("DefaultQuestGiverRef"))

    parts = relative_path.parts
    category_index = next(
        index
        for index, part in enumerate(parts)
        if part.casefold() == category.casefold()
    )

    return Quest(
        name=name,
        category=category,
        source=path,
        relative_path=tuple(parts[category_index + 1 : -1]),
        title=title,
        summary=_text(properties.get("Summary")),
        giver=giver,
        npcs=_quest_npcs(
            quest_object,
            steps,
            giver,
        ),
        steps=steps,
        rewards=_rewards(quest_object),
        money_reward=_int(properties.get("MoneyReward")),
        renown_reward=_int(properties.get("RenownReward")),
        village_trust_reward=_int(properties.get("VillageTrustReward")),
        village_prosperity_reward=_int(properties.get("VillageProsperityReward")),
    )
