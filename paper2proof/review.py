from uuid import uuid4

from paper2proof.artifacts.evidence import canonical_json, digest
from paper2proof.schemas.workflow import Claim, ClaimDraft, Paper, ReviewDraft, SpecVersion

REQUIRED_SETTINGS = {
    "method",
    "dataset",
    "baseline",
    "initialization",
    "iterations",
    "seeds",
    "metric",
}


def validate_citation(paper: Paper, span_id: str, quote: str):
    span = next((span for span in paper.spans if span.id == span_id), None)
    if span is None or quote not in span.text:
        raise ValueError("Citation must match an exact passage in a stored source span")
    return span


def make_claim(paper: Paper, draft: ClaimDraft, previous: Claim | None = None) -> Claim:
    validate_citation(paper, draft.span_id, draft.quote)
    return Claim(
        **draft.model_dump(),
        id=uuid4().hex,
        paper_id=paper.id,
        version=previous.version + 1 if previous else 1,
        previous_version_id=previous.id if previous else None,
    )


def make_spec(
    paper: Paper, claim: Claim, draft: ReviewDraft, previous: SpecVersion | None = None
) -> SpecVersion:
    validate_citation(paper, claim.span_id, claim.quote)
    blockers = []
    if claim.metric != "relative_l2_solution_error" or claim.unit != "dimensionless_ratio":
        blockers.append("Only dimensionless relative L2 solution error is currently supported.")
    if claim.method != "randomized_kaczmarz":
        blockers.append("Select and substantiate the supported randomized Kaczmarz method.")
    if claim.direction != "smaller_is_better":
        blockers.append("The supported evaluator requires smaller-is-better error.")
    if draft.target_relative_error is None or not draft.target_rationale.strip():
        blockers.append("A target and explicit rationale must be supplied before approval.")
    missing = REQUIRED_SETTINGS - draft.settings.keys()
    blockers.extend(f"Missing setting: {name}" for name in sorted(missing))
    for name, setting in draft.settings.items():
        if setting.value is None:
            blockers.append(f"Unresolved setting: {name}")
        if setting.origin == "paper_sourced":
            if not setting.source_span_id or not setting.source_quote:
                blockers.append(f"Sourced setting needs a citation: {name}")
            else:
                validate_citation(paper, setting.source_span_id, setting.source_quote)
    if draft.mode == "direct":
        blockers.append(
            "Direct reproduction is unavailable until paper-specific comparability is reviewed."
        )
    expected = {
        "method": "randomized_kaczmarz",
        "dataset": "synthetic_128x32_v1",
        "baseline": "zero_vector",
        "initialization": "zero_vector",
        "iterations": 512,
        "seeds": "7,23,41",
        "metric": "relative_l2_solution_error",
    }
    for name, value in expected.items():
        if name in draft.settings and draft.settings[name].value != value:
            blockers.append(f"Offline adapter only supports {name}={value}.")
    body = {
        **draft.model_dump(mode="json"),
        "claim_id": claim.id,
        "paper_id": paper.id,
        "version": previous.version + 1 if previous else 1,
        "previous_version_id": previous.id if previous else None,
        "evaluator_version": "linear-evaluator-v1",
    }
    return SpecVersion(
        **body, id=uuid4().hex, spec_hash=digest(canonical_json(body)), blockers=tuple(blockers)
    )


def verify_spec(spec: SpecVersion) -> None:
    body = spec.model_dump(mode="json", exclude={"id", "spec_hash", "blockers"})
    if digest(canonical_json(body)) != spec.spec_hash:
        raise ValueError("Frozen specification integrity check failed")
    if spec.blockers:
        raise ValueError("Unresolved specification blockers")


def default_review() -> ReviewDraft:
    from paper2proof.schemas.workflow import Setting

    values = {
        "method": "randomized_kaczmarz",
        "dataset": "synthetic_128x32_v1",
        "baseline": "zero_vector",
        "initialization": "zero_vector",
        "iterations": 512,
        "seeds": "7,23,41",
        "metric": "relative_l2_solution_error",
    }
    return ReviewDraft(
        settings={
            name: Setting(
                value=value,
                origin="assumed",
                rationale="Engineering adapter default; not extracted from paper.",
            )
            for name, value in values.items()
        },
        assumptions=("Synthetic data and reduced workload differ from the source paper.",),
    )
