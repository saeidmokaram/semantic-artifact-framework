# Semantic Artifact agent entry point

This repository contains the strict Semantic Artifact Directory Package `semantic-artifact-framework.sa/`. Its canonical meaning is in `semantic-artifact-framework.sa/knowledge.jsonld`; its append-only contribution and change history is in `semantic-artifact-framework.sa/history.jsonld`. `semantic-artifact-framework.sa/semantic-artifact.jsonld` is the fixed entry manifest and contains the reader policy. `README.md` is a human orientation view, not an independent source of meaning.

## Loading sequence

1. Read `semantic-artifact-framework.sa/semantic-artifact.jsonld` completely.
2. Apply its `reader_policy` and active governance profile.
3. Retrieve only the objects in `semantic-artifact-framework.sa/knowledge.jsonld` relevant to the current question or task, then follow their relations, evidence, counterarguments and source traces.
4. Consult `semantic-artifact-framework.sa/history.jsonld` whenever origin, contribution, review, authority, correction, supersession or historical state is material.
5. Inspect linked artifacts only when relevant and preserve every artifact's identity, release, governance and authority boundary.

## Public web fallback

When a chat or agent can read this repository's small files but cannot retrieve the large canonical knowledge or history files, use the generated agent-access projection at `https://saeidmokaram.github.io/semantic-artifact-framework/agent/`. Its HTML resources support browser-based readers and its parallel JSON resources support direct machine clients. Confirm its artifact identity and Git snapshot, use its type-sharded catalog to retrieve only the relevant object resources, and follow per-object history links when history is material. Verify the declared hashes when the canonical bytes are accessible; otherwise disclose reliance on the hash-bound projection. Treat every resource at that endpoint as a generated, noncanonical retrieval projection of the identified `.sa` package, not as another source of meaning. Report any inaccessible resource or integrity mismatch instead of filling the gap with assumptions.

If Git retrieval is unavailable but the complete package can be downloaded, read `https://saeidmokaram.github.io/semantic-artifact-framework/downloads/distribution.json`, fetch its declared archive, verify the SHA-256 value, extract it without renaming its `.sa` root or required entries, and apply the normal loading sequence above. The ZIP file and distribution descriptor are transport resources; the extracted `.sa` directory retains the canonical package roles.

## Operating rules

- Treat the represented work as the source of its claims; do not silently add model opinion or background knowledge.
- Label new reasoning as a derivation and identify its input object IDs. Label outside information as external context.
- Preserve the distinction among source material, observations, asserted facts, interpretations, conclusions and generated outputs.
- Preserve explicit gaps, disagreements, uncertainty, counterarguments and superseded states.
- When asked for the work's claims, counterarguments, evidence or risks, retrieve the corresponding represented objects. Do not replace the artifact's counterarguments with newly generated objections. Put relevant semantic object IDs in a compact trace after the ordinary-language answer rather than making metadata the main presentation.
- If the user explicitly requests additional criticism, hypotheses or alternatives beyond the represented artifact, separate and label them as derivation or external context in accordance with the manifest policy.
- Do not treat a projection, generated answer, mapping or implementation behaviour as canonical knowledge unless an attributed event accepts it under the declared governance policy.
- Do not infer authority from repository access, author order, tool use or the ability to propose a change.
- Structural validation does not prove semantic accuracy, completeness, safety, benefit or interoperability.

## Changing the artifact

A semantic change requires both:

1. an identified object or revision in `semantic-artifact-framework.sa/knowledge.jsonld`; and
2. a new attributed event in `semantic-artifact-framework.sa/history.jsonld`.

Never delete or rewrite a released contribution event to conceal an earlier state. Corrections, challenges, rejection and supersession are later events. Keep repository-specific documentation minimal; reusable meaning and policy belong in the semantic files.
