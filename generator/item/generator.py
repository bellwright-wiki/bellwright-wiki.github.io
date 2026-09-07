from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from .. import icon
from . import category, markdown, scanner
from .cache import AssetCache
from .schema.common import FieldExtractor
from .schema.mapping import schema_module

TITLE = "Items"


def _rows(
    items,
    fields: dict[str, FieldExtractor],
    icon_index,
    icon_out,
    icon_prefix,
):
    if not items:
        return [], []

    headers = list(fields)
    rows = []

    for item in items:
        context = {
            "path": item.path,
            "template": item.template,
            "category": item.category,
            "category_group": item.category_group or "",
            "icon": "",
            "damaged_item": item.damaged_item,
            "unbroken_parent": item.unbroken_parent,
        }

        icon_path = icon.find_icon(
            item.properties,
            icon_index,
        )

        if icon_path:
            destination = icon.copy_icon(
                icon_path,
                icon_out,
            )

            context["icon"] = (
                f'<img src="{icon_prefix}'
                f'assets/icons/{destination.name}" '
                f'alt="{item.stem}" width="48">'
            )

        rows.append(
            {
                name: extractor(
                    item.properties,
                    context,
                )
                for name, extractor in fields.items()
            }
        )

    rows.sort(
        key=lambda row: str(
            row.get(
                "Name",
                "",
            )
        ).lower()
    )

    return headers, rows


def _group_ancestors(
    index: category.CategoryIndex,
    node: category.CategoryNode,
) -> list[category.CategoryNode]:
    return [index.nodes[key] for key in node.group_ancestors]


def _is_single_category_group(
    node: category.CategoryNode,
    populated_categories,
) -> bool:
    return node.is_group and len(populated_categories[node.key]) == 1


def _category_path(
    index: category.CategoryIndex,
    node: category.CategoryNode,
    populated_categories,
) -> str:
    ancestors = _group_ancestors(
        index,
        node,
    )

    parts = [index.slug(group.title) for group in ancestors]

    singleton_group = None

    for group in reversed(ancestors):
        if _is_single_category_group(
            group,
            populated_categories,
        ):
            singleton_group = group
            break

    if singleton_group is not None:
        singleton_index = ancestors.index(singleton_group)

        parts = [index.slug(group.title) for group in ancestors[: singleton_index + 1]]

        return (
            "/".join(
                [
                    "items",
                    *parts,
                ]
            )
            + ".md"
        )

    parts.append(index.slug(node.title) + ".md")

    return "/".join(
        [
            "items",
            *parts,
        ]
    )


def _group_path(
    index: category.CategoryIndex,
    node: category.CategoryNode,
) -> str:
    ancestors = _group_ancestors(
        index,
        node,
    )

    parts = [index.slug(group.title) for group in ancestors]

    parts.append(index.slug(node.title) + ".md")

    return "/".join(
        [
            "items",
            *parts,
        ]
    )


def _relative_link(
    source: Path,
    target: Path,
) -> str:
    link = Path(
        os.path.relpath(
            target,
            source.parent,
        )
    ).as_posix()

    return link.removesuffix(".md")


def _category_link(
    index: category.CategoryIndex,
    node: category.CategoryNode,
    docs: Path,
    source: Path,
    populated_categories,
) -> str:
    target = docs / _category_path(
        index,
        node,
        populated_categories,
    )

    return _relative_link(
        source,
        target,
    )


def _has_items(
    node: category.CategoryNode,
    by_category,
    populated_categories,
) -> bool:
    if not node.is_group:
        return bool(by_category.get(node.key))

    return bool(populated_categories[node.key])


def _group_page_needed(
    node: category.CategoryNode,
    populated_categories,
) -> bool:
    return not _is_single_category_group(
        node,
        populated_categories,
    )


def _group_tree(
    index: category.CategoryIndex,
    node: category.CategoryNode,
    by_category,
    populated_categories,
    docs: Path,
    source: Path,
    indent: int = 0,
) -> list[str]:
    lines: list[str] = []
    prefix = "  " * indent

    for child in index.children(
        node,
        categories_only=False,
    ):
        if not _has_items(
            child,
            by_category,
            populated_categories,
        ):
            # Empty category nodes are structural only. Their
            # descendants remain part of the same visible tree.
            if not child.is_group:
                lines.extend(
                    _group_tree(
                        index,
                        child,
                        by_category,
                        populated_categories,
                        docs,
                        source,
                        indent,
                    )
                )

            continue

        if child.is_group:
            categories = populated_categories[child.key]

            if not categories:
                continue

            if _is_single_category_group(
                child,
                populated_categories,
            ):
                link = _category_link(
                    index,
                    categories[0],
                    docs,
                    source,
                    populated_categories,
                )

                lines.append(f"{prefix}- [{child.title}]({link})")
            else:
                lines.append(f"{prefix}- {child.title}")

                lines.extend(
                    _group_tree(
                        index,
                        child,
                        by_category,
                        populated_categories,
                        docs,
                        source,
                        indent + 1,
                    )
                )

            continue

        link = _category_link(
            index,
            child,
            docs,
            source,
            populated_categories,
        )

        lines.append(f"{prefix}- [{child.title}]({link})")

    return lines


def _write_category_pages(
    index: category.CategoryIndex,
    by_category,
    populated_categories,
    docs: Path,
    icon_index,
    icon_out: Path,
) -> list[dict]:
    pages: list[dict] = []

    root_groups = {node.key: node for node in index.roots() if node.is_group}

    for node in sorted(
        (
            node
            for node in index.nodes.values()
            if (not node.is_group and by_category.get(node.key))
        ),
        key=lambda node: node.title.casefold(),
    ):
        items = by_category[node.key]

        output = docs / _category_path(
            index,
            node,
            populated_categories,
        )

        ancestors = _group_ancestors(
            index,
            node,
        )

        parent = None
        parent_path = None
        grand_parent = None
        grand_parent_path = None

        if ancestors:
            parent_node = ancestors[-1]
            parent = parent_node.title

            if parent_node.key in root_groups and _group_page_needed(
                parent_node,
                populated_categories,
            ):
                parent_path = _group_path(
                    index,
                    parent_node,
                )

            if len(ancestors) > 1:
                grand_parent_node = ancestors[-2]
                grand_parent = grand_parent_node.title

                if grand_parent_node.key in root_groups and _group_page_needed(
                    grand_parent_node,
                    populated_categories,
                ):
                    grand_parent_path = _group_path(
                        index,
                        grand_parent_node,
                    )

        relative_depth = len(output.relative_to(docs).parts) - 1

        module = schema_module(
            index,
            node,
            items[0].template,
        )

        headers, rows = _rows(
            items,
            dict(getattr(module, "FIELDS", {})),
            icon_index,
            icon_out,
            "../" * relative_depth,
        )

        markdown.write_page(
            output,
            node.title,
            rows=rows,
            headers=headers,
            parent=parent,
            parent_path=parent_path,
            grand_parent=grand_parent,
            grand_parent_path=grand_parent_path,
        )

        relative = output.relative_to(docs).as_posix()

        schema = module.__name__.rsplit(
            ".",
            1,
        )[-1]

        print(f"\tGENERATED {relative} ({len(items)} items) using schema {schema}")

        pages.append(
            {
                "title": node.title,
                "slug": relative.removesuffix(".md"),
                "node": node,
            }
        )

    return pages


def _write_group_pages(
    index: category.CategoryIndex,
    by_category,
    populated_categories,
    docs: Path,
) -> list[dict]:
    pages: list[dict] = []

    groups = sorted(
        (
            node
            for node in index.roots()
            if (
                node.is_group
                and _has_items(
                    node,
                    by_category,
                    populated_categories,
                )
                and _group_page_needed(
                    node,
                    populated_categories,
                )
            )
        ),
        key=lambda node: node.title.casefold(),
    )

    for node in groups:
        output = docs / _group_path(
            index,
            node,
        )

        tree = _group_tree(
            index,
            node,
            by_category,
            populated_categories,
            docs,
            output,
        )

        markdown.write_tree_page(
            output,
            node.title,
            tree,
        )

        relative = output.relative_to(docs).as_posix()

        categories = populated_categories[node.key]

        print(f"\tGENERATED {relative} ({len(categories)} categories)")

        pages.append(
            {
                "title": node.title,
                "slug": relative.removesuffix(".md"),
                "node": node,
            }
        )

    return pages


def generate(
    assets: Path,
    docs: Path,
    icon_out: Path,
    icon_index: dict[str, Path],
) -> dict:
    asset_cache = AssetCache(assets)

    index = category.CategoryIndex.from_assets(asset_cache)

    items = list(
        scanner.discover_items(
            asset_cache,
            index,
        )
    )

    relationships = scanner.load_broken_relationships(asset_cache)

    by_parent: dict[str, str] = {}
    by_broken: dict[str, str] = {}

    for broken, (
        damaged,
        parent,
    ) in relationships.items():
        damaged = damaged or broken

        if parent:
            by_parent[parent] = damaged

        by_broken[damaged] = parent

    for item in items:
        item.damaged_item = by_parent.get(
            item.stem,
            "",
        )
        item.unbroken_parent = by_broken.get(
            item.stem,
            "",
        )

    by_category = defaultdict(list)

    for item in items:
        by_category[item.category_key].append(item)

    populated_categories = {
        node.key: tuple(
            index.nodes[key]
            for key in node.descendant_categories
            if by_category.get(key)
        )
        for node in index.nodes.values()
        if node.is_group
    }

    category_pages = _write_category_pages(
        index,
        by_category,
        populated_categories,
        docs,
        icon_index,
        icon_out,
    )

    group_pages = _write_group_pages(
        index,
        by_category,
        populated_categories,
        docs,
    )

    category_by_node = {page["node"].key: page for page in category_pages}

    group_by_node = {page["node"].key: page for page in group_pages}

    pages: list[dict] = []

    for node in index.roots():
        if not _has_items(
            node,
            by_category,
            populated_categories,
        ):
            continue

        if node.is_group:
            if _group_page_needed(
                node,
                populated_categories,
            ):
                page = group_by_node.get(node.key)
            else:
                categories = populated_categories[node.key]

                if len(categories) == 1:
                    category_node = categories[0]

                    page = {
                        "title": node.title,
                        "slug": _category_path(
                            index,
                            category_node,
                            populated_categories,
                        ).removesuffix(".md"),
                    }
                else:
                    page = None
        else:
            page = category_by_node.get(node.key)

        if not page:
            continue

        pages.append(
            {
                "title": page["title"],
                "slug": page["slug"],
            }
        )

    print(f"Item definitions discovered: {len(items)}")

    return {
        "title": TITLE,
        "pages": pages,
    }
