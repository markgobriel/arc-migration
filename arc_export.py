#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


@dataclass
class Bookmark:
    title: str
    url: str


@dataclass
class Folder:
    title: str
    children: List[Union["Folder", Bookmark]] = field(default_factory=list)


@dataclass
class ArcNode:
    node_id: str
    parent_id: Optional[str]
    title: Optional[str]
    data: Dict[str, Any]
    order: int


@dataclass
class ExportStats:
    containers_total: int
    containers_selected: int
    spaces_detected: int
    spaces_included: int
    folders: int
    tabs: int


def find_default_sidebar_path() -> Optional[str]:
    if sys.platform == "darwin":
        candidate = os.path.expanduser(
            "~/Library/Application Support/Arc/StorableSidebar.json"
        )
        if os.path.isfile(candidate):
            return candidate
        return None
    if sys.platform.startswith("win"):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None
        packages_dir = os.path.join(local_app_data, "Packages")
        if not os.path.isdir(packages_dir):
            return None
        for name in sorted(os.listdir(packages_dir)):
            if not name.startswith("TheBrowserCompany.Arc"):
                continue
            candidate = os.path.join(
                packages_dir,
                name,
                "LocalCache",
                "Local",
                "Arc",
                "StorableSidebar.json",
            )
            if os.path.isfile(candidate):
                return candidate
    return None


def find_list_for_key(obj: Any, key: str) -> Optional[List[Any]]:
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], list):
            return obj[key]
        for value in obj.values():
            found = find_list_for_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_list_for_key(value, key)
            if found is not None:
                return found
    return None


def find_containers_anywhere(obj: Any) -> Optional[List[Any]]:
    if isinstance(obj, dict):
        containers = obj.get("containers")
        if isinstance(containers, list):
            return containers
        for value in obj.values():
            found = find_containers_anywhere(value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_containers_anywhere(value)
            if found is not None:
                return found
    return None


def extract_containers(data: Dict[str, Any]) -> List[Any]:
    root = data.get("root", data)
    if isinstance(root, dict):
        sidebar = root.get("sidebar")
        if isinstance(sidebar, dict) and isinstance(sidebar.get("containers"), list):
            return sidebar["containers"]
    containers = find_containers_anywhere(root)
    if containers is None:
        return []
    return containers


def select_containers(
    containers: List[Any], all_containers: bool
) -> List[Tuple[int, Any]]:
    if not containers:
        return []
    if all_containers:
        return list(enumerate(containers))
    if len(containers) > 1 and isinstance(containers[1], dict):
        items = find_list_for_key(containers[1], "items")
        if items:
            return [(1, containers[1])]
    for index, container in enumerate(containers):
        items = find_list_for_key(container, "items")
        if items:
            return [(index, container)]
    return [(0, containers[0])]


def is_folder_like(node: ArcNode) -> bool:
    if not isinstance(node.data, dict):
        return False
    for key in ("list", "tabGroup", "itemContainer"):
        if key in node.data:
            return True
    return False


def get_node_title(node: ArcNode, default: str) -> str:
    candidates = [node.title]
    if isinstance(node.data, dict):
        candidates.extend([node.data.get("title"), node.data.get("name")])
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return default


def get_tab_info(node: ArcNode) -> Optional[Bookmark]:
    if not isinstance(node.data, dict):
        return None
    tab = node.data.get("tab")
    if not isinstance(tab, dict):
        return None
    url = tab.get("savedURL") or tab.get("url") or tab.get("URL")
    if not isinstance(url, str) or not url.strip():
        return None
    title = tab.get("savedTitle") or tab.get("title") or node.title
    if not isinstance(title, str) or not title.strip():
        title = url
    return Bookmark(title=title.strip(), url=url.strip())


def space_is_pinned(space: Dict[str, Any]) -> Optional[bool]:
    for key in ("isPinned", "pinned", "isPinnedSpace", "is_pinned"):
        value = space.get(key)
        if isinstance(value, bool):
            return value
    data = space.get("data")
    if isinstance(data, dict):
        for key in ("isPinned", "pinned", "isPinnedSpace", "is_pinned"):
            value = data.get(key)
            if isinstance(value, bool):
                return value
    return None


def gather_ids_by_key(obj: Any, match_key) -> Iterable[str]:
    ids: List[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if match_key(key):
                if isinstance(value, str):
                    ids.append(value)
                elif isinstance(value, list):
                    ids.extend([v for v in value if isinstance(v, str)])
            if isinstance(value, (dict, list)):
                ids.extend(gather_ids_by_key(value, match_key))
    elif isinstance(obj, list):
        for value in obj:
            ids.extend(gather_ids_by_key(value, match_key))
    return ids


def extract_space_roots(space: Dict[str, Any], nodes: Dict[str, ArcNode]) -> List[str]:
    candidate_ids = set()
    direct_keys = [
        "itemContainerId",
        "itemContainerID",
        "itemContainerIds",
        "itemContainerIDs",
        "rootItemContainerId",
        "rootItemContainerID",
        "rootItemId",
        "rootItemID",
        "rootItemIds",
        "rootItemIDs",
        "rootId",
        "rootID",
        "rootIds",
        "rootIDs",
    ]
    for key in direct_keys:
        value = space.get(key)
        if isinstance(value, str):
            candidate_ids.add(value)
        elif isinstance(value, list):
            candidate_ids.update([v for v in value if isinstance(v, str)])
    data = space.get("data")
    if isinstance(data, dict):
        for key in direct_keys:
            value = data.get(key)
            if isinstance(value, str):
                candidate_ids.add(value)
            elif isinstance(value, list):
                candidate_ids.update([v for v in value if isinstance(v, str)])

    def key_matcher(key: str) -> bool:
        key_lower = key.lower()
        return "itemcontainer" in key_lower or key_lower in {
            "rootid",
            "rootids",
            "rootitemid",
            "rootitemids",
        }

    candidate_ids.update(gather_ids_by_key(space, key_matcher))
    valid_ids = [node_id for node_id in candidate_ids if node_id in nodes]
    return sorted(valid_ids, key=lambda node_id: nodes[node_id].order)


def build_children_from_ids(
    node_ids: Iterable[str],
    nodes: Dict[str, ArcNode],
    children_map: Dict[str, List[str]],
) -> List[Union[Folder, Bookmark]]:
    children: List[Union[Folder, Bookmark]] = []
    seen_tabs = set()
    for node_id in node_ids:
        child = build_tree(node_id, nodes, children_map, set())
        if child is None:
            continue
        if isinstance(child, Bookmark):
            key = (child.title, child.url)
            if key in seen_tabs:
                continue
            seen_tabs.add(key)
        children.append(child)
    return children


def build_tree(
    node_id: str,
    nodes: Dict[str, ArcNode],
    children_map: Dict[str, List[str]],
    visiting: set,
) -> Optional[Union[Folder, Bookmark]]:
    if node_id in visiting:
        return None
    node = nodes.get(node_id)
    if node is None:
        return None
    visiting.add(node_id)
    tab_info = get_tab_info(node)
    if tab_info is not None:
        visiting.remove(node_id)
        return tab_info

    child_ids = children_map.get(node_id, [])
    if not is_folder_like(node) and not child_ids:
        visiting.remove(node_id)
        return None

    title = get_node_title(node, "Untitled Folder")
    folder = Folder(title=title)
    seen_tabs = set()
    for child_id in child_ids:
        child = build_tree(child_id, nodes, children_map, visiting)
        if child is None:
            continue
        if isinstance(child, Bookmark):
            key = (child.title, child.url)
            if key in seen_tabs:
                continue
            seen_tabs.add(key)
        folder.children.append(child)
    visiting.remove(node_id)
    return folder


def parse_container(
    container: Dict[str, Any],
    container_index: int,
    include_unpinned: bool,
) -> Tuple[List[Union[Folder, Bookmark]], int, int]:
    items = find_list_for_key(container, "items") or []
    nodes: Dict[str, ArcNode] = {}
    for order, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        node_id = item.get("id")
        if not isinstance(node_id, str) or not node_id:
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        parent_id = (
            item.get("parentID")
            or item.get("parentId")
            or item.get("parent_id")
        )
        if isinstance(parent_id, str) and not parent_id.strip():
            parent_id = None
        title = item.get("title") if isinstance(item.get("title"), str) else None
        nodes[node_id] = ArcNode(
            node_id=node_id,
            parent_id=parent_id,
            title=title,
            data=data,
            order=order,
        )

    children_map: Dict[str, List[str]] = {}
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            children_map.setdefault(node.parent_id, []).append(node.node_id)

    ordered_nodes = sorted(nodes.values(), key=lambda item: item.order)
    root_ids = [
        node.node_id
        for node in ordered_nodes
        if not node.parent_id or node.parent_id not in nodes
    ]

    spaces = find_list_for_key(container, "spaces")
    spaces_detected = len(spaces) if isinstance(spaces, list) else 0
    spaces_included = 0

    top_nodes: List[Union[Folder, Bookmark]] = []
    if isinstance(spaces, list) and spaces:
        used_ids = set()
        space_nodes: List[Folder] = []
        for index, space in enumerate(spaces):
            if not isinstance(space, dict):
                continue
            pinned = space_is_pinned(space)
            if pinned is False and not include_unpinned:
                continue
            title = space.get("title") or space.get("name") or f"Space {index + 1}"
            root_ids_for_space = extract_space_roots(space, nodes)
            if not root_ids_for_space:
                continue
            children = build_children_from_ids(
                root_ids_for_space, nodes, children_map
            )
            if not children:
                continue
            space_nodes.append(Folder(title=str(title), children=children))
            used_ids.update(root_ids_for_space)
            spaces_included += 1

        if space_nodes:
            remaining_root_ids = [node_id for node_id in root_ids if node_id not in used_ids]
            remaining_nodes = build_children_from_ids(
                remaining_root_ids, nodes, children_map
            )
            top_nodes = space_nodes + remaining_nodes
        else:
            root_children = build_children_from_ids(root_ids, nodes, children_map)
            if root_children:
                top_nodes = [
                    Folder(
                        title=f"Arc Export (Container {container_index + 1})",
                        children=root_children,
                    )
                ]
    else:
        root_children = build_children_from_ids(root_ids, nodes, children_map)
        if root_children:
            top_nodes = [
                Folder(
                    title=f"Arc Export (Container {container_index + 1})",
                    children=root_children,
                )
            ]

    return top_nodes, spaces_detected, spaces_included


def parse_arc_sidebar(
    data: Dict[str, Any],
    include_unpinned: bool = False,
    all_containers: bool = False,
) -> Tuple[List[Union[Folder, Bookmark]], ExportStats]:
    containers = extract_containers(data)
    selected = select_containers(containers, all_containers)

    all_nodes: List[Union[Folder, Bookmark]] = []
    spaces_detected_total = 0
    spaces_included_total = 0

    for container_index, container in selected:
        if not isinstance(container, dict):
            continue
        container_nodes, spaces_detected, spaces_included = parse_container(
            container, container_index, include_unpinned
        )
        spaces_detected_total += spaces_detected
        spaces_included_total += spaces_included
        if not container_nodes:
            continue
        if all_containers and len(selected) > 1:
            all_nodes.append(
                Folder(
                    title=f"Arc Export (Container {container_index + 1})",
                    children=container_nodes,
                )
            )
        else:
            all_nodes.extend(container_nodes)

    folders, tabs = count_nodes(all_nodes)
    stats = ExportStats(
        containers_total=len(containers),
        containers_selected=len(selected),
        spaces_detected=spaces_detected_total,
        spaces_included=spaces_included_total,
        folders=folders,
        tabs=tabs,
    )
    return all_nodes, stats


def count_nodes(nodes: List[Union[Folder, Bookmark]]) -> Tuple[int, int]:
    folders = 0
    tabs = 0

    def walk(node: Union[Folder, Bookmark]) -> None:
        nonlocal folders, tabs
        if isinstance(node, Folder):
            folders += 1
            for child in node.children:
                walk(child)
        else:
            tabs += 1

    for node in nodes:
        walk(node)

    return folders, tabs


def render_bookmarks_html(nodes: List[Union[Folder, Bookmark]]) -> str:
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]
    lines.extend(render_nodes(nodes, depth=1))
    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"


def render_nodes(
    nodes: List[Union[Folder, Bookmark]], depth: int
) -> List[str]:
    indent = "    " * depth
    lines: List[str] = []
    for node in nodes:
        if isinstance(node, Folder):
            title = html.escape(node.title)
            lines.append(f"{indent}<DT><H3>{title}</H3>")
            lines.append(f"{indent}<DL><p>")
            lines.extend(render_nodes(node.children, depth=depth + 1))
            lines.append(f"{indent}</DL><p>")
        else:
            title = html.escape(node.title)
            url = html.escape(node.url, quote=True)
            lines.append(f"{indent}<DT><A HREF=\"{url}\">{title}</A>")
    return lines


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_output(path: str, contents: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(contents)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export Arc Browser Spaces/Folders/Tabs to Netscape bookmarks HTML."
    )
    parser.add_argument(
        "--input",
        help="Optional path to StorableSidebar.json",
    )
    parser.add_argument(
        "--output",
        default="./arc_bookmarks.html",
        help="Output HTML path (default: ./arc_bookmarks.html)",
    )
    parser.add_argument(
        "--include-unpinned",
        action="store_true",
        help="Include unpinned spaces when pinned/unpinned is available",
    )
    parser.add_argument(
        "--all-containers",
        action="store_true",
        help="Export from every container, not just the default container",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug counts and detected structures",
    )

    args = parser.parse_args(argv)

    input_path = args.input or find_default_sidebar_path()
    if not input_path or not os.path.isfile(input_path):
        print(
            "Could not find Arc sidebar data (StorableSidebar.json).\n"
            "Open Arc, locate StorableSidebar.json in your profile data, "
            "then rerun with --input /path/to/StorableSidebar.json.",
            file=sys.stderr,
        )
        return 2

    try:
        data = load_json(input_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read JSON: {exc}", file=sys.stderr)
        return 2

    nodes, stats = parse_arc_sidebar(
        data,
        include_unpinned=args.include_unpinned,
        all_containers=args.all_containers,
    )
    if not nodes:
        print("No exportable items found in the sidebar data.", file=sys.stderr)
        return 2

    html_output = render_bookmarks_html(nodes)
    try:
        write_output(args.output, html_output)
    except OSError as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 2

    if args.verbose:
        print(f"Input: {input_path}")
        print(f"Containers: {stats.containers_total} (selected: {stats.containers_selected})")
        if stats.spaces_detected:
            print(
                "Spaces detected: "
                f"{stats.spaces_detected} (included: {stats.spaces_included})"
            )
        else:
            print("Spaces detected: 0")
        print(f"Folders: {stats.folders}")
        print(f"Tabs: {stats.tabs}")
        print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
