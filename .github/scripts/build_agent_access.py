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


PROJECTION_VERSION = "0.2.0"
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


def write_html(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(title)}</title>"
        "<main style=\"max-width:70rem;margin:3rem auto;padding:0 1.25rem;"
        "font:16px/1.5 system-ui,sans-serif;overflow-wrap:anywhere\">"
        f"<h1>{html.escape(title)}</h1>{body}</main></html>\n",
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
    object_web_urls = {
        identifier: object_urls[identifier][:-5] + ".html"
        for identifier in object_by_id
    }
    known_ids = set(object_by_id)
    history_urls = {
        identifier: f"{base_url}/history/{resource_name(identifier)}"
        for identifier in object_by_id
        if events_by_target.get(identifier)
    }
    history_web_urls = {
        identifier: history_urls[identifier][:-5] + ".html"
        for identifier in history_urls
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

        object_document = {
            "@context": knowledge_context,
            "@graph": [item],
            "_access": access,
        }
        object_filename = resource_name(identifier)
        write_json(object_root / object_filename, object_document)
        reference_links = "".join(
            f'<li><a href="{html.escape(reference["url"])[:-5]}.html">'
            f'{html.escape(reference["id"])}</a></li>'
            for reference in access["referenced_objects"]
        )
        history_link = (
            f'<p><a href="{html.escape(history_web_urls[identifier])}">'
            "Contribution and change history for this object</a></p>"
            if identifier in history_web_urls
            else ""
        )
        write_html(
            object_root / (object_filename[:-5] + ".html"),
            str(item.get("label") or identifier),
            "<p>Generated, noncanonical access projection of semantic object "
            f"<code>{html.escape(identifier)}</code>.</p>"
            + history_link
            + ("<h2>Referenced objects</h2><ul>" + reference_links + "</ul>" if reference_links else "")
            + "<h2>Canonical object content</h2><pre>"
            + html.escape(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True))
            + "</pre>",
        )

        catalog_item = {
            "id": identifier,
            "type": item.get("@type"),
            "label": item.get("label"),
            "status": item.get("status"),
            "review_status": item.get("review_status"),
            "tags": as_list(item.get("tags")),
            "object_url": object_urls[identifier],
            "object_web_url": object_web_urls[identifier],
        }
        if identifier in history_urls:
            catalog_item["history_url"] = history_urls[identifier]
            catalog_item["history_web_url"] = history_web_urls[identifier]
        catalog.append(catalog_item)

        target_events = events_by_target.get(identifier, [])
        if target_events:
            history_document = {
                "@context": history_context,
                "@graph": target_events,
                "_access": {
                    "projection_status": "generated-noncanonical-access-projection",
                    "artifact_snapshot": args.snapshot,
                    "target_object_id": identifier,
                    "canonical_file": "semantic-artifact-framework.sa/history.jsonld",
                    "canonical_file_sha256": hashes["history.jsonld"],
                    "object_url": object_urls[identifier],
                    "object_web_url": object_web_urls[identifier],
                },
            }
            history_filename = resource_name(identifier)
            write_json(history_root / history_filename, history_document)
            write_html(
                history_root / (history_filename[:-5] + ".html"),
                f"History — {item.get('label') or identifier}",
                f'<p><a href="{html.escape(object_web_urls[identifier])}">'
                "Return to semantic object</a></p>"
                "<p>Generated, noncanonical access projection of the events targeting "
                f"<code>{html.escape(identifier)}</code>.</p><pre>"
                + html.escape(
                    json.dumps(target_events, ensure_ascii=False, indent=2, sort_keys=True)
                )
                + "</pre>",
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
        "web_url": f"{base_url}/",
        "instructions_url": f"{repository_url}/blob/{args.snapshot}/AGENTS.md",
        "manifest_url": f"{base_url}/manifest.jsonld",
        "manifest_web_url": f"{base_url}/manifest.html",
        "catalog_url": f"{base_url}/catalog/index.json",
        "catalog_web_url": f"{base_url}/catalog/",
        "root_object_url": object_urls.get(str(root_id)),
        "root_object_web_url": object_web_urls.get(str(root_id)),
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
        "operating_contract": [
            "Treat the identified .sa package as canonical; this site is only its hash-bound access projection.",
            "Read the manifest and apply its reader_policy before answering substantive questions.",
            "Retrieve relevant represented objects and follow material relations, evidence, counterarguments and history.",
            "For claims, counterarguments, evidence or risks, use represented objects and include their IDs in a compact trace; do not substitute newly generated analysis.",
            "Label new reasoning as DERIVATION with its input object IDs; label outside material as EXTERNAL CONTEXT.",
            "Preserve explicit gaps, uncertainty, disagreement and superseded state; report inaccessible required resources.",
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
        shard_web_url = shard_url[:-5] + ".html"
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
            {
                "object_type": type_name,
                "count": len(items),
                "url": shard_url,
                "web_url": shard_web_url,
            }
        )
        rows = "".join(
            "<li>"
            f'<a href="{html.escape(item["object_web_url"])}">'
            f'{html.escape(str(item.get("label") or item["id"]))}</a> '
            f'<code>{html.escape(item["id"])}</code> — '
            f'{html.escape(str(item.get("status") or "status not declared"))}'
            "</li>"
            for item in items
        )
        write_html(
            agent_root / "catalog" / (filename[:-5] + ".html"),
            f"Semantic objects — {type_name}",
            "<p>Generated, noncanonical catalog shard.</p><ul>" + rows + "</ul>",
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
    shard_links = "".join(
        f'<li><a href="{html.escape(shard["web_url"])}">'
        f'{html.escape(shard["object_type"])}</a> ({shard["count"]})</li>'
        for shard in catalog_shards
    )
    write_html(
        agent_root / "catalog" / "index.html",
        "Semantic Artifact object catalog",
        "<p>Choose one or more small type-based catalogs, then retrieve only the "
        "objects relevant to the current question.</p><ul>" + shard_links + "</ul>",
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
    write_html(
        agent_root / "manifest.html",
        "Semantic Artifact manifest",
        "<p>This is an HTML access rendering of the hash-identified canonical "
        "manifest.</p><pre>"
        + html.escape(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        + "</pre>",
    )

    entry_links = "".join(
        (
            f'<li><a href="{html.escape(entry[link_key])}">'
            f'{html.escape(label)}</a></li>'
        )
        for link_key, label in (
            ("manifest_web_url", "Manifest"),
            ("catalog_web_url", "Object catalog"),
            ("root_object_web_url", "Root work object"),
        )
        if entry.get(link_key)
    )
    write_html(
        agent_root / "index.html",
        "Semantic Artifact agent entry",
        "<p>This is a generated, noncanonical retrieval projection. Read the "
        "manifest, select relevant catalog shards, retrieve the required objects, "
        "and follow their references and history links.</p><h2>Operating contract</h2><ol>"
        + "".join(
            f"<li>{html.escape(rule)}</li>" for rule in entry["operating_contract"]
        )
        + "</ol><h2>Resources</h2><ul>"
        + entry_links
        + "</ul><h2>Entry metadata</h2><pre>"
        + html.escape(json.dumps(entry, ensure_ascii=False, indent=2, sort_keys=True))
        + "</pre>",
    )

    bootstrap = f"Load and follow the Semantic Artifact at {base_url}/, then wait for my task."
    (output / "llms.txt").write_text(
        "# Semantic Artifact Framework — agent access\n\n"
        + bootstrap
        + "\n\n"
        + "Operating contract:\n"
        + "\n".join(f"- {rule}" for rule in entry["operating_contract"])
        + "\n\n"
        + f"Web entry: {base_url}/\n"
        + f"JSON entry: {base_url}/index.json\n"
        + f"Catalog: {base_url}/catalog/\n"
        + f"Manifest: {base_url}/manifest.html\n",
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
        f"<p><a href=\"agent/\">Agent entry</a> · "
        f"<a href=\"agent/catalog/\">Object catalog</a> · "
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
    if len(list(object_root.glob("*.html"))) != expected_object_files:
        raise SystemExit("object HTML projection count mismatch")
    if len(list(history_root.glob("*.json"))) != expected_history_files:
        raise SystemExit("history projection count mismatch")
    if len(list(history_root.glob("*.html"))) != expected_history_files:
        raise SystemExit("history HTML projection count mismatch")

    print(
        f"Built agent access projection for {len(objects)} objects and "
        f"{len(events)} history events at {output}"
    )


if __name__ == "__main__":
    main()
