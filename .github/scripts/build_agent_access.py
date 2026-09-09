#!/usr/bin/env python3
"""Build a static, hash-bound agent-access projection of a .sa package."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECTION_VERSION = "0.1.0"
REQUIRED_FILES = (
    "semantic-artifact.jsonld",
    "knowledge.jsonld",
    "history.jsonld",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--snapshot", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resource_name(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest() + ".json"


def type_resource_name(type_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", type_name.lower()).strip("-")
    return (slug or "untyped") + ".json"


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def referenced_object_ids(value: Any, known_ids: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            found.update(referenced_object_ids(child, known_ids))
    elif isinstance(value, list):
        for child in value:
            found.update(referenced_object_ids(child, known_ids))
    elif isinstance(value, str) and value in known_ids:
        found.add(value)
    return found


def main() -> None:
    args = parse_args()
    package = args.package.resolve()
    output = args.output.resolve()
    base_url = args.base_url.rstrip("/")
    repository_url = args.repository_url.rstrip("/")

    if package.suffix != ".sa" or not package.is_dir():
        raise SystemExit("--package must be an existing directory ending in .sa")
    if output.exists():
        raise SystemExit("--output must not already exist")
    if (
        output == Path("/")
        or output == package
        or output in package.parents
        or package in output.parents
    ):
        raise SystemExit("unsafe output location")

    paths = {name: package / name for name in REQUIRED_FILES}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise SystemExit(f"missing required package files: {', '.join(missing)}")

    manifest = load_json(paths["semantic-artifact.jsonld"])
    knowledge = load_json(paths["knowledge.jsonld"])
    history = load_json(paths["history.jsonld"])
    hashes = {name: file_hash(path) for name, path in paths.items()}
    objects = knowledge.get("@graph")
    events = history.get("@graph")
    if not isinstance(objects, list) or not isinstance(events, list):
        raise SystemExit("knowledge and history must each contain an @graph array")

    object_by_id: dict[str, dict[str, Any]] = {}
    for item in objects:
        identifier = item.get("@id") if isinstance(item, dict) else None
        if not isinstance(identifier, str) or not identifier:
            raise SystemExit("every knowledge object must have a non-empty @id")
        if identifier in object_by_id:
            raise SystemExit(f"duplicate knowledge object ID: {identifier}")
        object_by_id[identifier] = item

    events_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unscoped_events: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("@id"), str):
            raise SystemExit("every history event must have a non-empty @id")
        if event["@id"] in event_ids:
            raise SystemExit(f"duplicate history event ID: {event['@id']}")
        event_ids.add(event["@id"])
        target = event.get("target")
        if isinstance(target, str):
            if target not in object_by_id:
                raise SystemExit(
                    f"history event {event['@id']} targets missing object {target}"
                )
            events_by_target[target].append(event)
        else:
            unscoped_events.append(event)

    object_urls = {
        identifier: f"{base_url}/objects/{resource_name(identifier)}"
        for identifier in object_by_id
    }
    known_ids = set(object_by_id)
    history_urls = {
        identifier: f"{base_url}/history/{resource_name(identifier)}"
        for identifier in object_by_id
        if events_by_target.get(identifier)
    }

    output.mkdir(parents=True)
    agent_root = output / "agent"
    object_root = agent_root / "objects"
    history_root = agent_root / "history"

    knowledge_context = knowledge.get("@context", {})
    history_context = history.get("@context", {})
    catalog: list[dict[str, Any]] = []
    unresolved_relations: list[dict[str, str]] = []

    for identifier, item in object_by_id.items():
        relation_links: list[dict[str, str]] = []
        for relation in as_list(item.get("relations")):
            if not isinstance(relation, dict):
                continue
            target = relation.get("target")
            predicate = relation.get("predicate")
            if not isinstance(target, str):
                continue
            link = {"target": target}
            if isinstance(predicate, str):
                link["predicate"] = predicate
            if target in object_urls:
                link["url"] = object_urls[target]
            else:
                unresolved_relations.append(
                    {"source": identifier, "target": target, "predicate": str(predicate or "")}
                )
            relation_links.append(link)

        access = {
            "projection_status": "generated-noncanonical-access-projection",
            "artifact_snapshot": args.snapshot,
            "object_id": identifier,
            "canonical_file": "semantic-artifact-framework.sa/knowledge.jsonld",
            "canonical_file_sha256": hashes["knowledge.jsonld"],
            "relations": relation_links,
            "referenced_objects": [
                {"id": target, "url": object_urls[target]}
                for target in sorted(referenced_object_ids(item, known_ids) - {identifier})
            ],
        }
        if identifier in history_urls:
            access["history_url"] = history_urls[identifier]

        write_json(
            object_root / resource_name(identifier),
            {"@context": knowledge_context, "@graph": [item], "_access": access},
        )

        catalog_item = {
            "id": identifier,
            "type": item.get("@type"),
            "label": item.get("label"),
            "status": item.get("status"),
            "review_status": item.get("review_status"),
            "tags": as_list(item.get("tags")),
            "object_url": object_urls[identifier],
        }
        if identifier in history_urls:
            catalog_item["history_url"] = history_urls[identifier]
        catalog.append(catalog_item)

        target_events = events_by_target.get(identifier, [])
        if target_events:
            write_json(
                history_root / resource_name(identifier),
                {
                    "@context": history_context,
                    "@graph": target_events,
                    "_access": {
                        "projection_status": "generated-noncanonical-access-projection",
                        "artifact_snapshot": args.snapshot,
                        "target_object_id": identifier,
                        "canonical_file": "semantic-artifact-framework.sa/history.jsonld",
                        "canonical_file_sha256": hashes["history.jsonld"],
                        "object_url": object_urls[identifier],
                    },
                },
            )

    catalog.sort(key=lambda item: item["id"])
    root_id = manifest.get("@id")
    if not isinstance(root_id, str) or root_id not in object_by_id:
        raise SystemExit("manifest @id must identify an object in the knowledge graph")
    entry = {
        "projection_type": "SemanticArtifactAgentAccessProjection",
        "projection_version": PROJECTION_VERSION,
        "projection_status": "generated-noncanonical-access-projection",
        "notice": (
            "This endpoint is a generated retrieval projection. The .sa package is "
            "canonical. Confirm the declared snapshot, verify file hashes when canonical "
            "bytes are accessible, and otherwise disclose reliance on this projection."
        ),
        "artifact": {
            "id": root_id,
            "title": manifest.get("title"),
            "format": manifest.get("format"),
            "format_version": manifest.get("format_version"),
            "governance_profile": manifest.get("governance_profile", {}).get("profile"),
        },
        "artifact_snapshot": args.snapshot,
        "repository_url": repository_url,
        "instructions_url": f"{repository_url}/blob/{args.snapshot}/AGENTS.md",
        "manifest_url": f"{base_url}/manifest.jsonld",
        "catalog_url": f"{base_url}/catalog/index.json",
        "root_object_url": object_urls.get(str(root_id)),
        "canonical_files": [
            {
                "role": role,
                "path": f"{package.name}/{name}",
                "sha256": hashes[name],
                "repository_url": f"{repository_url}/blob/{args.snapshot}/{package.name}/{name}",
            }
            for role, name in (
                ("manifest", "semantic-artifact.jsonld"),
                ("canonical_knowledge", "knowledge.jsonld"),
                ("append_only_history", "history.jsonld"),
            )
        ],
        "counts": {
            "knowledge_objects": len(objects),
            "history_events": len(events),
            "objects_with_history": len(history_urls),
            "unscoped_history_events": len(unscoped_events),
            "unresolved_internal_relations": len(unresolved_relations),
        },
        "retrieval_sequence": [
            "Read the manifest and apply its reader_policy.",
            "Use the catalog to locate objects relevant to the question.",
            "Retrieve those object resources and follow material relation URLs.",
            "Retrieve per-object history when origin, review, authority or change matters.",
            "Preserve the distinction between canonical content and this generated access projection.",
        ],
    }

    write_json(agent_root / "index.json", entry)
    catalog_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in catalog:
        catalog_by_type[str(item.get("type") or "Untyped")].append(item)
    catalog_shards = []
    for type_name, items in sorted(catalog_by_type.items()):
        filename = type_resource_name(type_name)
        shard_url = f"{base_url}/catalog/{filename}"
        write_json(
            agent_root / "catalog" / filename,
            {
                "projection_status": "generated-noncanonical-access-projection",
                "artifact_id": root_id,
                "artifact_snapshot": args.snapshot,
                "canonical_knowledge_sha256": hashes["knowledge.jsonld"],
                "object_type": type_name,
                "objects": items,
            },
        )
        catalog_shards.append(
            {"object_type": type_name, "count": len(items), "url": shard_url}
        )
    write_json(
        agent_root / "catalog" / "index.json",
        {
            "projection_status": "generated-noncanonical-access-projection",
            "artifact_id": root_id,
            "artifact_snapshot": args.snapshot,
            "canonical_knowledge_sha256": hashes["knowledge.jsonld"],
            "total_objects": len(catalog),
            "root_object_url": object_urls.get(str(root_id)),
            "catalog_shards": catalog_shards,
        },
    )
    write_json(
        agent_root / "unresolved-relations.json",
        {
            "artifact_id": root_id,
            "artifact_snapshot": args.snapshot,
            "relations": unresolved_relations,
        },
    )
    if unscoped_events:
        write_json(
            agent_root / "unscoped-history.json",
            {
                "@context": history_context,
                "@graph": unscoped_events,
                "_access": {
                    "projection_status": "generated-noncanonical-access-projection",
                    "artifact_snapshot": args.snapshot,
                },
            },
        )

    # The manifest is small enough for constrained web readers and remains hash-bound
    # to the canonical file declared in index.json.
    (agent_root / "manifest.jsonld").write_bytes(
        paths["semantic-artifact.jsonld"].read_bytes()
    )

    bootstrap = (
        f"Load and follow the Semantic Artifact at {repository_url}, starting with "
        "AGENTS.md. If the canonical knowledge or history files cannot be fetched, "
        f"use the generated access projection at {base_url}/index.json. Confirm the "
        "artifact identity and snapshot, report inaccessible required resources, and "
        "then wait for the user's task."
    )
    (output / "llms.txt").write_text(
        "# Semantic Artifact Framework — agent access\n\n"
        + bootstrap
        + "\n\n"
        + f"Entry: {base_url}/index.json\n"
        + f"Catalog: {base_url}/catalog/index.json\n"
        + f"Manifest: {base_url}/manifest.jsonld\n",
        encoding="utf-8",
    )
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "index.html").write_text(
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Semantic Artifact Framework — agent access</title>"
        "<main style=\"max-width:48rem;margin:4rem auto;padding:0 1.25rem;"
        "font:18px/1.55 system-ui,sans-serif\">"
        "<h1>Semantic Artifact Framework — agent access</h1>"
        "<p>This is a generated, noncanonical retrieval projection of the public "
        "Semantic Artifact. Its entry document identifies the canonical snapshot "
        "and integrity hashes.</p>"
        f"<p><a href=\"agent/index.json\">Agent entry</a> · "
        f"<a href=\"agent/catalog/index.json\">Object catalog</a> · "
        f"<a href=\"llms.txt\">Plain-text instructions</a> · "
        f"<a href=\"{html.escape(repository_url)}\">Canonical repository</a></p>"
        "<h2>Minimal instruction</h2><blockquote>"
        + html.escape(bootstrap)
        + "</blockquote></main></html>\n",
        encoding="utf-8",
    )

    expected_object_files = len(objects)
    expected_history_files = len(events_by_target)
    if len(list(object_root.glob("*.json"))) != expected_object_files:
        raise SystemExit("object projection count mismatch")
    if len(list(history_root.glob("*.json"))) != expected_history_files:
        raise SystemExit("history projection count mismatch")

    print(
        f"Built agent access projection for {len(objects)} objects and "
        f"{len(events)} history events at {output}"
    )


if __name__ == "__main__":
    main()
