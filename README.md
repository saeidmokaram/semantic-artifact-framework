# Semantic Artifact Framework

**From Documents to Semantic Artifacts, by Saeid Mokaram**

The framework proposes a knowledge-first form for human, agentic and mixed work. Instead of treating a document, report, paper or README as the primary container, a represented work maintains a governed semantic artifact containing its knowledge, evidence, questions, decisions, alternatives, attempts, failures, interpretations, provenance and history. Documents and interfaces are generated as purpose-specific projections; code, designs, actions and other consequential outputs are traceable derivatives.

> The document becomes a view, not the sole boundary of the represented knowledge.

The artifact belongs to the represented work rather than to one document, agent, model, provider, user, session or organisation. Its scope may be research, a theory, an investigation, software, a policy, a creative work, a story world, an organisation's continuing activity or another bounded body of knowledge.

This repository is both the proposal's canonical semantic form and its first self-demonstrating instance. It is a proposal and evolving specification, not a validated or adopted standard.

## The `.sa` package

The canonical artifact is contained by [`semantic-artifact-framework.sa/`](semantic-artifact-framework.sa/), a visible Semantic Artifact Directory Package. Its three required entries have fixed names:

- [`semantic-artifact.jsonld`](semantic-artifact-framework.sa/semantic-artifact.jsonld) — identity, governance, loading contract, policies and linked artifacts.
- [`knowledge.jsonld`](semantic-artifact-framework.sa/knowledge.jsonld) — canonical semantic state.
- [`history.jsonld`](semantic-artifact-framework.sa/history.jsonld) — append-only contribution and semantic-change history.

[`AGENTS.md`](AGENTS.md) and this README are concise host-platform access adapters. [`validation/saf-core.shacl.ttl`](semantic-artifact-framework.sa/validation/saf-core.shacl.ttl) contains proposed structural constraints. [`LICENSE`](LICENSE) states the reuse and attribution terms. None is an additional source of the work's substantive meaning.

## Use it with an AI assistant

[`AGENTS.md`](AGENTS.md) is the provider-neutral instruction and loading entry point. Some coding agents discover this filename automatically, but general AI chats may not. In any assistant that can access public GitHub repositories, begin with this single instruction:

> Load and follow the Semantic Artifact at https://github.com/saeidmokaram/semantic-artifact-framework, starting with `AGENTS.md`; confirm the artifact identity and report any required file you cannot access, then wait for my task.

The assistant should fetch the repository and follow `AGENTS.md` into the `.sa` package; the README alone is not the represented knowledge. If its web tools cannot retrieve the large canonical files, `AGENTS.md` directs it to a [generated, hash-bound access projection](https://saeidmokaram.github.io/semantic-artifact-framework/agent/index.json) that exposes a compact catalog, individual semantic objects and per-object history. If the assistant cannot read either public location, upload `AGENTS.md` together with the complete `semantic-artifact-framework.sa/` directory, or upload its three required files while preserving their names and roles. No particular AI provider, model or chat product is required.

To start a new artifact, copy the `.sa` directory structure as `<work-name>.sa/`, assign a new identity and governance profile, and replace the canonical knowledge and history with records belonging to the new work. Loose renamed files are import material, not a conforming strict package, until normalised.

## Important boundaries

- The `.sa` directory is the current attached exchange profile; JSON-LD and folders are not the identity of the framework or mandatory internal storage technologies.
- Original sources, observations, factual assertions, interpretations and derivations remain distinguishable.
- History is non-erasing: corrections, challenges, rejections and supersession append events instead of rewriting earlier contribution records.
- Multiple artifacts may be loaded and queried together without silently merging their authority or canonical state.
- Generated answers, mappings and projections are noncanonical until accepted through the declared governance process.
- Structural validation does not establish truth, completeness, practical benefit, safety or cross-platform interoperability.

## Related implementations

- [Semantic Artifact Explorer](https://github.com/saeidmokaram/semantic-artifact-explorer) — an optional view application for interactive exploration of one or more artifacts.
- [Semantic Artifact Toolkit](https://github.com/saeidmokaram/semantic-artifact-toolkit) — deterministic validation, reference and semantic-closure operations.

These tools are independently versioned semantic artifacts. The framework does not depend on either one.

## Licence

Unless a source record says otherwise, the original semantic content and specification material are available under [CC BY 4.0](LICENSE). Commercial and non-commercial use and adaptation are permitted with appropriate credit to Saeid Mokaram, a link to the licence and identification of material changes.
