from pathlib import Path


def _render_group(group: dict) -> list[str]:
    """Render one generator group."""
    lines = [
        '<div class="data-group" markdown="1">',
        "",
        f"## {group['title']}",
        "",
    ]

    lines.extend(
        f"- [{page['title']}]({page['slug']})"
        for page in sorted(
            group["pages"],
            key=lambda page: page["title"].lower(),
        )
    )

    lines.extend(
        [
            "",
            "</div>",
            "",
        ]
    )

    return lines


def _render_data(page_groups: list[dict]) -> list[str]:
    """Render generator groups in a CSS grid."""
    lines = [
        '<div class="data-groups">',
        "",
    ]

    for group in page_groups:
        lines.extend(_render_group(group))

    lines.extend(
        [
            "</div>",
            "",
        ]
    )

    return lines


def write_index_page(
    output: Path,
    page_groups: list[dict],
    logo: Path,
) -> None:
    """Write the root documentation index."""
    output.parent.mkdir(parents=True, exist_ok=True)

    version = (
        (output.parent.parent / "assets" / "version")
        .read_text(encoding="utf-8")
        .strip()
    )

    lines = [
        "---",
        "layout: default",
        "title: Bellwright Wiki",
        (
            "description: Explore the world of Bellwright with a searchable wiki "
            "and database covering quests, items, characters, crafting, resources, "
            "locations, and rewards."
        ),
        "---",
        '<div class="logo"></div>',
        "",
        "# Bellwright Wiki",
        "",
        "A searchable **Bellwright wiki and database** with quests, items, "
        "NPCs, rewards, recipes, resources, crafting, locations, "
        "and other game data.",
        "",
        f"![Game Version](https://img.shields.io/badge/Game%20Version-{version}-black?logo=unrealengine)",
        "[![GitHub](https://img.shields.io/badge/Source%20Code-GitHub-black?logo=github)](https://github.com/r0ute/bw-wiki)",
        *_render_data(page_groups),
    ]

    output.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
