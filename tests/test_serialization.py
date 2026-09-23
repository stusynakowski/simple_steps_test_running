"""
Serialization: construct, write, load, run.

Two different things get serialized, and confusing them is the usual mistake:

* **the recipe** (`to_json` / `from_json`) — the steps and their arguments,
  no values. What you commit to a repo or paste into a ticket.
* **the session** (`export_session` / `import_session`) — the recipe *plus*
  every value produced so far. What you save to resume a half-finished run
  tomorrow.

Each is tested through a real file on disk rather than a string handed
straight back, because "it round-trips in memory" and "I can reload it next
week" are not the same claim. The reload also uses a **freshly built
registry and engine**, since the interesting failure is a snapshot that only
loads in the process that wrote it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from simple_steps_core import (
    CodecRegistry,
    CoreEngine,
    Operation,
    SnapshotError,
    StepStatus,
    Workflow,
)

from capability.parity import unwrap
from example0_identity_workflow import steps


@dataclass
class Reading:
    """A type `json` cannot encode on its own — the point of a codec."""

    label: str
    value: float


def reading_codecs() -> CodecRegistry:
    codecs = CodecRegistry()
    codecs.register(
        "reading", Reading,
        lambda r: {"label": r.label, "value": r.value},
        lambda d: Reading(d["label"], d["value"]),
    )
    return codecs


def _values_in_recipe(text: str) -> list[str]:
    """Step ids whose computed value is embedded in a `to_json` recipe.

    Structural, not a substring search: whether pydantic emits `[[1, 2, 3]`
    or `[[1,2,3]` is not the thing under test.
    """
    carried = []
    for step in json.loads(text):
        output = step.get("output") or {}
        if output.get("value") is not None:
            carried.append(step["step_id"])
    return carried


@pytest.fixture
def ran():
    workflow = steps.build_flow().build()
    workflow.run()
    return workflow


@pytest.fixture
def expected():
    return steps.run_plain()


# ── the recipe ───────────────────────────────────────────────────────────
@pytest.mark.capability("persist.wf_json")
def test_the_recipe_round_trips_through_a_file_and_still_runs(tmp_path, expected):
    """Construct → write → load → run, with nothing shared but the file."""
    path = tmp_path / "workflow.json"
    path.write_text(steps.build_flow().build().to_json())
    assert path.stat().st_size > 0

    restored = Workflow.from_json(
        path.read_text(), CoreEngine(steps.build_registry()), session_id="restored"
    )
    restored.run()
    assert restored["step5"].output.value == expected["step5"]


@pytest.mark.capability("persist.recipe_only")
@pytest.mark.xfail(
    strict=True,
    reason="`to_json` documents 'payloads excluded' but dumps list[Step], and "
           "Step embeds output.value inline. Every computed value travels with "
           "the recipe, so sharing a workflow definition ships its data.",
)
def test_the_recipe_carries_no_values(ran):
    """A recipe saved *after* a run must still be only the steps."""
    carried = _values_in_recipe(ran.to_json())
    assert not carried, f"computed values leaked into the recipe: {carried}"


@pytest.mark.capability("persist.recipe_only")
def test_the_recipe_currently_embeds_every_computed_value(ran):
    """Pin today's behaviour, because the docstring promises the opposite.

    This matters beyond tidiness: a workflow run over real data and then
    shared as a 'recipe' carries that data with it. Checked structurally —
    a substring search would only be testing pydantic's whitespace.
    """
    carried = _values_in_recipe(ran.to_json())
    assert set(carried) == {"step1", "step2", "step3", "step4", "step5"}, (
        "every step's value is inline in the so-called recipe"
    )
    assert "payloads" not in ran.to_json(), "to_json is not a snapshot either"


# ── the session ──────────────────────────────────────────────────────────
@pytest.mark.capability("persist.session")
def test_a_finished_session_reloads_from_disk_with_every_value(tmp_path, ran, expected):
    path = tmp_path / "session.json"
    path.write_text(ran.export_session_json())

    restored = Workflow.import_session_json(
        path.read_text(), CoreEngine(steps.build_registry())
    )
    for step_id, value in expected.items():
        # step4 is a map, so its output is a MapResult rather than a list.
        assert unwrap(restored[step_id].output.value) == value, (
            f"{step_id} did not survive the round trip"
        )


@pytest.mark.capability("persist.session", "exec.rerun")
def test_a_half_finished_session_resumes_where_it_stopped(tmp_path, expected):
    """The case the feature exists for: stop, save, reload tomorrow, carry on."""
    workflow = steps.build_flow().build()
    workflow.run_step("step1")
    workflow.run_step("step2")

    path = tmp_path / "half.json"
    path.write_text(workflow.export_session_json())

    resumed = Workflow.import_session_json(
        path.read_text(), CoreEngine(steps.build_registry())
    )
    assert resumed["step2"].status is StepStatus.COMPLETED
    assert resumed["step3"].status is StepStatus.PENDING, "too much was restored"

    resumed.run()
    assert resumed["step5"].output.value == expected["step5"]


@pytest.mark.capability("persist.resources_excluded")
def test_a_snapshot_never_contains_a_resource(tmp_path):
    """Resources are connections and credentials — they must not be written."""
    from example1_basic_math_workflow import steps as math_steps

    workflow = math_steps.build_flow().build()
    workflow.run_step("step1")
    text = workflow.export_session_json()

    assert "MathSettings" not in text
    assert "factor" not in text, "a resource's contents reached the snapshot"


# ── custom types ─────────────────────────────────────────────────────────
@pytest.mark.capability("persist.codecs")
def test_an_unserializable_value_fails_loudly_with_an_actionable_message():
    """The failure must say what to do, not just that json gave up."""
    registry = steps.build_registry()
    registry.register("make_reading", lambda: Reading("x", 2.5))
    workflow = Workflow(CoreEngine(registry), session_id="nocodec")
    workflow["step1"] = Operation(step_id="step1", name="make_reading")
    workflow.run()

    with pytest.raises(SnapshotError) as excinfo:
        workflow.export_session_json()
    message = str(excinfo.value)
    assert "Reading" in message
    assert "CodecRegistry.register" in message, f"not actionable: {message}"


@pytest.mark.capability("persist.codecs")
def test_a_custom_codec_carries_a_non_json_type_through_a_file(tmp_path):
    registry = steps.build_registry()
    registry.register("make_reading", lambda: Reading("x", 2.5))
    workflow = Workflow(CoreEngine(registry), session_id="codec")
    workflow["step1"] = Operation(step_id="step1", name="make_reading")
    workflow.run()

    codecs = reading_codecs()
    path = tmp_path / "codec.json"
    path.write_text(workflow.export_session_json(codecs=codecs))

    restored = Workflow.import_session_json(
        path.read_text(), CoreEngine(registry), codecs=codecs
    )
    value = restored["step1"].output.value
    assert isinstance(value, Reading), f"decoded to {type(value).__name__}"
    assert value == Reading("x", 2.5)


@pytest.mark.capability("persist.codecs")
def test_loading_without_the_codec_that_wrote_it_fails_rather_than_guessing(tmp_path):
    """A silent dict-instead-of-Reading would be worse than an error."""
    registry = steps.build_registry()
    registry.register("make_reading", lambda: Reading("x", 2.5))
    workflow = Workflow(CoreEngine(registry), session_id="codec")
    workflow["step1"] = Operation(step_id="step1", name="make_reading")
    workflow.run()

    text = workflow.export_session_json(codecs=reading_codecs())

    try:
        restored = Workflow.import_session_json(text, CoreEngine(registry))
    except SnapshotError:
        return                                    # the good outcome
    value = restored["step1"].output.value
    assert not isinstance(value, Reading), "decoded without a codec — impossible"
    pytest.fail(
        "loading without the writing codec silently produced "
        f"{type(value).__name__} ({value!r}) instead of raising"
    )
