# Capability coverage

Generated from the test run — do not edit by hand. Declare capabilities in
`capability/catalogue.py`; claim them with `@pytest.mark.capability("<id>")`.

| tested against | |
| --- | --- |
| library | simple-steps-core 0.1.0 |
| commit | b0245a3022d3 |
| source | https://github.com/stusynakowski/simple-steps-core.git |
| install | wheel / site-packages |
| python | 3.12.13 |
| platform | Darwin arm64 |
| hard deps | notebook>=7.6.0, pydantic>=2.6 |

| verdict | count | share |
| --- | ---: | ---: |
| works | 41 | 72% |
| awkward | 0 | 0% |
| gap | 4 | 7% |
| broken | 0 | 0% |
| untested | 12 | 21% |

**57 declared capabilities.**

## Core capabilities not yet proven

- `orch.map` — Apply a tool to each item (mode='map') (**gap**)
- `flow.unknown_ref` — A reference to a missing step fails validation (**gap**)
- `inspect.validate` — `wf.validate()` checks tools, refs and resources (**gap**)

## authoring

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `auth.plain` | Register a plain sync function as a tool | core | works | `test_each_tool_alone_reproduces_its_plain_function[example0_identity]`, `test_each_tool_alone_reproduces_its_plain_function[example1_math]`, `test_every_plain_function_is_a_registered_tool[example0_identity]`, `test_every_plain_function_is_a_registered_tool[example1_math]`, `test_plain_functions_become_listable_tools` |
| OK | `auth.async` | Register an async function as a tool | core | works | `test_an_async_step_receives_its_injected_resource`, `test_each_tool_alone_reproduces_its_plain_function[example0_identity]`, `test_each_tool_alone_reproduces_its_plain_function[example1_math]` |
| OK | `auth.schema` | Type annotations become an input JSON Schema | core | works | `test_annotations_become_a_schema_with_optional_params` |
| OK | `auth.defaults` | Optional params with defaults are non-required | core | works | `test_annotations_become_a_schema_with_optional_params` |
| OK | `auth.dual_mode` | A registered tool is callable deferred and immediate | important | works | `test_a_tool_runs_immediately_and_defers`, `test_each_tool_alone_reproduces_its_plain_function[example0_identity]`, `test_each_tool_alone_reproduces_its_plain_function[example1_math]` |
| OK | `auth.docstring` | The docstring's first paragraph becomes the description | important | works | `test_annotations_become_a_schema_with_optional_params` |
| ?? | `auth.guardrails` | Per-argument guardrails reject bad values | important | untested | — |
| ?? | `auth.output_schema` | The return annotation becomes an output schema | important | untested | — |

## resources

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `res.inject` | A `Resource()` param is injected at run time | core | works | `test_an_async_step_receives_its_injected_resource` |
| OK | `res.hidden` | Resource params are absent from the input schema | core | works | `test_a_resource_param_is_absent_from_the_input_schema` |
| OK | `res.lazy` | A resource factory is built lazily on first use | core | works | `test_declaring_a_resource_does_not_build_it` |
| ?? | `res.named` | `Resource("key")` overrides the container key | important | untested | — |
| OK | `res.missing` | A missing resource raises a clear, named error | core | works | `test_a_missing_resource_raises_a_named_error` |
| OK | `res.check` | `check`/`check_all` run a hello-world per resource | important | works | `test_a_resource_check_runs_a_hello_world` |
| OK | `res.isolation` | Each session clones resources, no cross-talk | core | works | `test_two_sessions_do_not_share_a_resource_instance` |
| OK | `res.declared_missing` | A workflow reports missing resources before running | core | works | `test_a_workflow_reports_a_missing_resource_before_running`, `test_the_flow_validates_before_anything_runs[example0_identity]`, `test_the_flow_validates_before_anything_runs[example1_math]` |
| ?? | `res.bound_tools` | Tools bind exclusively to one resource | important | untested | — |
| OK | `res.adapter_free` | An existing function can be registered as a resource-bound tool | important | works | `test_only_declared_adapters_differ_from_the_plain_function[example0_identity]`, `test_only_declared_adapters_differ_from_the_plain_function[example1_math]` |
| ?? | `res.qualified_ids` | A bound tool's id is `<resource>-<tool>` | important | untested | — |

<details><summary>Notes &amp; sharp edges</summary>

- `res.named` — Was silently ignored before the resource-binding work; verify on a fresh build.
- `res.bound_tools` — New. Qualified ids are `<resource>-<tool>`; needs a wheel rebuild to test.
- `res.adapter_free` — Example 1 needs one adapter for this reason; see ExampleSpec.adapted, which is asserted to stay small.
- `res.qualified_ids` — Breaking for bare orchestrator ids (`map`) unless aliased.

</details>

## orchestration

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `orch.single` | Run a step once (mode='single') | core | works | `test_source_runs_once_and_yields_the_nested_collection`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]` |
| OK | `orch.source` | A step with no upstream produces the initial collection | core | works | `test_source_runs_once_and_yields_the_nested_collection` |
| -- | `orch.map` | Apply a tool to each item (mode='map') | core | gap | `test_map_yields_per_item_outcomes_rather_than_a_list`, `test_orchestrating_over_a_bare_map_step_should_not_silently_corrupt`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]`, `test_validation_should_reject_a_collapse_over_a_bare_map_step` |
| OK | `orch.expand` | Flat-map each item into many (mode='expand') | core | works | `test_expand_flattens_one_level_without_a_bespoke_tool`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]` |
| OK | `orch.filter` | Keep items where the tool is truthy (mode='filter') | core | works | `test_filter_keeps_only_the_items_that_qualify`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]` |
| OK | `orch.collapse` | Reduce a collection to one value (mode='collapse') | core | works | `test_a_type_changing_reduce_needs_an_explicit_initial`, `test_collapse_reduces_the_collection_to_one_value`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]` |
| OK | `orch.identity` | `identity` reshapes with no bespoke tool | important | works | `test_expand_flattens_one_level_without_a_bespoke_tool` |
| OK | `orch.concurrency` | Bounded concurrency across items | core | works | `test_the_async_flow_runs_to_completion` |
| OK | `orch.retries` | Per-item retries | core | works | `test_a_transient_failure_is_retried_until_it_succeeds`, `test_an_item_that_exhausts_its_retries_is_collected_as_a_failure` |
| OK | `orch.on_error_collect` | on_error='collect' isolates per-item failure | core | works | `test_an_item_that_exhausts_its_retries_is_collected_as_a_failure`, `test_one_poisoned_item_does_not_sink_the_batch` |
| OK | `orch.on_error_fail_fast` | on_error='fail_fast' aborts on first failure | important | works | `test_fail_fast_aborts_the_step_and_records_it` |
| OK | `orch.on_error_skip` | on_error='skip' silently drops failures | important | works | `test_skip_drops_the_failure_silently` |
| OK | `orch.empty` | An empty collection flows through without error | core | works | `test_a_filter_that_keeps_nothing_does_not_break_the_steps_after_it` |
| OK | `orch.shared_args` | Constant kwargs are passed to every sub-call | core | works | `test_a_constant_argument_reaches_every_sub_call` |
| -- | `orch.nested` | An orchestrated step can drive another orchestration | nice | gap | `test_a_map_can_drive_a_nested_orchestration` |

<details><summary>Notes &amp; sharp edges</summary>

- `orch.source` — Today 'source' is a ToolDefinition *type*, not an orchestrator mode.
- `orch.map` — ASYMMETRY: map yields a MapResult (ok/failed), while expand and filter yield flat lists. Consumers must handle both.
- `orch.collapse` — Called `collapse`, not `reduce`. Needs a 2-arg combiner, so it cannot default to `identity` the way map/filter/expand do.
- `orch.nested` — Unverified. Likely the sharpest edge in the library.

</details>

## dataflow

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `flow.literal` | Literal arguments pass through unchanged | core | works | `test_source_runs_once_and_yields_the_nested_collection` |
| OK | `flow.step_ref` | `"step1"` resolves to that step's output | core | works | `test_the_flow_validates_before_anything_runs`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]` |
| OK | `flow.field_ref` | `"step1.total"` resolves a field of an output | core | works | `test_a_type_changing_reduce_needs_an_explicit_initial` |
| ?? | `flow.index_ref` | `"step1.rows[0]"` resolves an index | important | untested | — |
| ?? | `flow.type_check` | References are type-checked before running | important | untested | — |
| -- | `flow.unknown_ref` | A reference to a missing step fails validation | core | gap | `test_a_reference_to_a_step_that_does_not_exist_fails_validation`, `test_a_typoed_reference_degrades_to_a_literal_string` |

## execution

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `exec.run_all` | Run a whole workflow synchronously | core | works | `test_every_step_completes`, `test_every_step_completes[example0_identity]`, `test_every_step_completes[example1_math]`, `test_the_final_value_matches_plain_python[example0_identity]`, `test_the_final_value_matches_plain_python[example1_math]` |
| OK | `exec.arun_all` | Run a whole workflow asynchronously | core | works | `test_every_step_completes[example0_identity]`, `test_every_step_completes[example1_math]`, `test_the_async_flow_runs_to_completion` |
| OK | `exec.step` | Run one step at a time | core | works | `test_a_flow_can_be_advanced_one_step_at_a_time` |
| ?? | `exec.stage` | Run a named/numbered stage | important | untested | — |
| OK | `exec.failure_isolated` | A failed step is recorded, not raised | core | works | `test_fail_fast_aborts_the_step_and_records_it`, `test_one_poisoned_item_does_not_sink_the_batch` |
| OK | `exec.rerun` | Re-running a step replaces its output | important | works | `test_running_the_same_flow_twice_gives_the_same_answer[example0_identity]`, `test_running_the_same_flow_twice_gives_the_same_answer[example1_math]` |
| ?? | `exec.sync_in_async` | Sync `run()` refuses to nest in a running loop | important | untested | — |

<details><summary>Notes &amp; sharp edges</summary>

- `exec.sync_in_async` — Known sharp edge: notebooks run an event loop already.

</details>

## inspection

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| -- | `inspect.validate` | `wf.validate()` checks tools, refs and resources | core | gap | `test_a_reference_to_a_step_that_does_not_exist_fails_validation`, `test_the_flow_validates_before_anything_runs`, `test_the_flow_validates_before_anything_runs[example0_identity]`, `test_the_flow_validates_before_anything_runs[example1_math]`, `test_validation_should_reject_a_collapse_over_a_bare_map_step` |
| OK | `inspect.info` | Every object has an `info()` summary table | important | works | `test_a_workflow_can_be_inspected_without_running_it` |
| OK | `inspect.repr` | Every object has a dense one-line `__repr__` | important | works | `test_a_workflow_can_be_inspected_without_running_it` |
| OK | `inspect.preview` | `wf.preview(step)` shows the first N rows | important | works | `test_a_workflow_can_be_inspected_without_running_it` |
| ?? | `inspect.shape` | A step announces its output shape before running | important | untested | — |
| OK | `inspect.tools` | The registered tool contracts are listable | core | works | `test_every_plain_function_is_a_registered_tool[example0_identity]`, `test_every_plain_function_is_a_registered_tool[example1_math]`, `test_plain_functions_become_listable_tools` |

## persistence

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `persist.wf_json` | A workflow round-trips through JSON | core | works | `test_a_json_round_trip_still_produces_the_same_answer[example0_identity]`, `test_a_json_round_trip_still_produces_the_same_answer[example1_math]`, `test_a_workflow_round_trips_through_json_without_its_resources` |
| ?? | `persist.session` | A session snapshot round-trips with its data | important | untested | — |
| ?? | `persist.codecs` | Custom types survive via codecs | important | untested | — |
| OK | `persist.resources_excluded` | Resources are never serialized | core | works | `test_a_json_round_trip_still_produces_the_same_answer[example0_identity]`, `test_a_json_round_trip_still_produces_the_same_answer[example1_math]`, `test_a_workflow_round_trips_through_json_without_its_resources` |
