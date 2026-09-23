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
| works | 61 | 87% |
| awkward | 0 | 0% |
| gap | 6 | 9% |
| broken | 0 | 0% |
| untested | 3 | 4% |

**70 declared capabilities.**

## Core capabilities not yet proven

- `orch.map` — Apply a tool to each item (mode='map') (**gap**)
- `flow.unknown_ref` — A reference to a missing step fails validation (**gap**)
- `inspect.validate` — `wf.validate()` checks tools, refs and resources (**gap**)
- `persist.recipe_only` — The recipe (`to_json`) excludes computed values (**gap**)

## authoring

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `auth.plain` | Register a plain sync function as a tool | core | works | `test_each_tool_alone_reproduces_its_plain_function[example0_identity]`, `test_each_tool_alone_reproduces_its_plain_function[example1_math]`, `test_every_plain_function_is_a_registered_tool[example0_identity]`, `test_every_plain_function_is_a_registered_tool[example1_math]`, `test_plain_functions_become_listable_tools`, `test_tool_registry_alone` |
| OK | `auth.async` | Register an async function as a tool | core | works | `test_an_async_step_receives_its_injected_resource`, `test_each_tool_alone_reproduces_its_plain_function[example0_identity]`, `test_each_tool_alone_reproduces_its_plain_function[example1_math]` |
| OK | `auth.schema` | Type annotations become an input JSON Schema | core | works | `test_annotations_become_a_schema_with_optional_params` |
| OK | `auth.defaults` | Optional params with defaults are non-required | core | works | `test_annotations_become_a_schema_with_optional_params` |
| OK | `auth.dual_mode` | A registered tool is callable deferred and immediate | important | works | `test_a_single_tool_runs_with_no_workflow_engine_or_session`, `test_a_tool_runs_immediately_and_defers`, `test_each_tool_alone_reproduces_its_plain_function[example0_identity]`, `test_each_tool_alone_reproduces_its_plain_function[example1_math]` |
| OK | `auth.docstring` | The docstring's first paragraph becomes the description | important | works | `test_annotations_become_a_schema_with_optional_params` |
| OK | `auth.guardrails` | Per-argument guardrails reject bad values | important | works | `test_a_guardrail_rejects_a_bad_argument_before_the_tool_runs` |
| OK | `auth.output_schema` | The return annotation becomes an output schema | important | works | `test_the_return_annotation_becomes_an_output_schema` |

## resources

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `res.inject` | A `Resource()` param is injected at run time | core | works | `test_an_async_step_receives_its_injected_resource` |
| OK | `res.hidden` | Resource params are absent from the input schema | core | works | `test_a_resource_param_is_absent_from_the_input_schema` |
| OK | `res.lazy` | A resource factory is built lazily on first use | core | works | `test_declaring_a_resource_does_not_build_it`, `test_resource_container_alone` |
| ?? | `res.named` | `Resource("key")` overrides the container key | important | untested | — |
| OK | `res.missing` | A missing resource raises a clear, named error | core | works | `test_a_missing_resource_raises_a_named_error` |
| OK | `res.check` | `check`/`check_all` run a hello-world per resource | important | works | `test_a_resource_check_runs_a_hello_world` |
| OK | `res.isolation` | Each session clones resources, no cross-talk | core | works | `test_session_manager_alone`, `test_the_app_facade_end_to_end`, `test_two_sessions_do_not_share_a_resource_instance` |
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
| OK | `flow.literal` | Literal arguments pass through unchanged | core | works | `test_reference_resolver_alone`, `test_source_runs_once_and_yields_the_nested_collection` |
| OK | `flow.step_ref` | `"step1"` resolves to that step's output | core | works | `test_reference_resolver_alone`, `test_the_flow_validates_before_anything_runs`, `test_the_workflow_matches_plain_python_at_every_phase[example0_identity]`, `test_the_workflow_matches_plain_python_at_every_phase[example1_math]` |
| OK | `flow.field_ref` | `"step1.total"` resolves a field of an output | core | works | `test_a_type_changing_reduce_needs_an_explicit_initial` |
| -- | `flow.index_ref` | `"step1.rows[0]"` resolves an index | important | gap | `test_a_bracket_index_is_currently_ignored_entirely`, `test_a_bracket_index_selects_one_element_of_a_step_output` |
| OK | `flow.type_check` | References are type-checked before running | important | works | `test_references_are_type_checked_before_the_workflow_runs` |
| -- | `flow.unknown_ref` | A reference to a missing step fails validation | core | gap | `test_a_reference_to_a_step_that_does_not_exist_fails_validation`, `test_a_typoed_reference_degrades_to_a_literal_string` |

## execution

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `exec.run_all` | Run a whole workflow synchronously | core | works | `test_every_step_completes`, `test_every_step_completes[example0_identity]`, `test_every_step_completes[example1_math]`, `test_the_final_value_matches_plain_python[example0_identity]`, `test_the_final_value_matches_plain_python[example1_math]` |
| OK | `exec.arun_all` | Run a whole workflow asynchronously | core | works | `test_every_step_completes[example0_identity]`, `test_every_step_completes[example1_math]`, `test_the_async_flow_runs_to_completion` |
| OK | `exec.step` | Run one step at a time | core | works | `test_a_flow_can_be_advanced_one_step_at_a_time`, `test_a_workflow_can_be_built_and_run_one_step_at_a_time` |
| OK | `exec.stage` | Run a named/numbered stage | important | works | `test_steps_can_be_grouped_into_stages_and_run_a_stage_at_a_time` |
| OK | `exec.failure_isolated` | A failed step is recorded, not raised | core | works | `test_fail_fast_aborts_the_step_and_records_it`, `test_one_poisoned_item_does_not_sink_the_batch` |
| OK | `exec.rerun` | Re-running a step replaces its output | important | works | `test_a_half_finished_session_resumes_where_it_stopped`, `test_a_step_can_be_replaced_and_re_run_without_rebuilding`, `test_running_the_same_flow_twice_gives_the_same_answer[example0_identity]`, `test_running_the_same_flow_twice_gives_the_same_answer[example1_math]` |
| OK | `exec.sync_in_async` | Sync `run()` refuses to nest in a running loop | important | works | `test_sync_run_refuses_to_drive_an_orchestrator_inside_a_running_loop` |

<details><summary>Notes &amp; sharp edges</summary>

- `exec.sync_in_async` — Known sharp edge: notebooks run an event loop already.

</details>

## inspection

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| -- | `inspect.validate` | `wf.validate()` checks tools, refs and resources | core | gap | `test_a_reference_to_a_step_that_does_not_exist_fails_validation`, `test_the_flow_validates_before_anything_runs`, `test_the_flow_validates_before_anything_runs[example0_identity]`, `test_the_flow_validates_before_anything_runs[example1_math]`, `test_validation_should_reject_a_collapse_over_a_bare_map_step` |
| OK | `inspect.info` | Every object has an `info()` summary table | important | works | `test_a_workflow_can_be_inspected_without_running_it`, `test_every_object_can_be_looked_at_in_a_repl` |
| OK | `inspect.repr` | Every object has a dense one-line `__repr__` | important | works | `test_a_workflow_can_be_inspected_without_running_it`, `test_every_object_can_be_looked_at_in_a_repl` |
| OK | `inspect.preview` | `wf.preview(step)` shows the first N rows | important | works | `test_a_workflow_can_be_inspected_without_running_it`, `test_every_object_can_be_looked_at_in_a_repl` |
| OK | `inspect.shape` | A step announces its output shape before running | important | works | `test_a_step_can_be_inspected_before_it_has_run` |
| OK | `inspect.tools` | The registered tool contracts are listable | core | works | `test_every_plain_function_is_a_registered_tool[example0_identity]`, `test_every_plain_function_is_a_registered_tool[example1_math]`, `test_plain_functions_become_listable_tools`, `test_the_app_lists_its_tools_for_discovery` |

## persistence

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `persist.wf_json` | A workflow round-trips through JSON | core | works | `test_a_json_round_trip_still_produces_the_same_answer[example0_identity]`, `test_a_json_round_trip_still_produces_the_same_answer[example1_math]`, `test_a_workflow_can_be_built_from_json_rather_than_python`, `test_a_workflow_round_trips_through_json_without_its_resources`, `test_the_recipe_round_trips_through_a_file_and_still_runs` |
| -- | `persist.recipe_only` | The recipe (`to_json`) excludes computed values | core | gap | `test_the_recipe_carries_no_values`, `test_the_recipe_currently_embeds_every_computed_value` |
| OK | `persist.session` | A session snapshot round-trips with its data | important | works | `test_a_finished_session_reloads_from_disk_with_every_value`, `test_a_half_finished_session_resumes_where_it_stopped`, `test_a_session_snapshot_round_trips_with_its_data` |
| OK | `persist.codecs` | Custom types survive via codecs | important | works | `test_a_custom_codec_carries_a_non_json_type_through_a_file`, `test_an_unserializable_value_fails_loudly_with_an_actionable_message`, `test_loading_without_the_codec_that_wrote_it_fails_rather_than_guessing` |
| OK | `persist.resources_excluded` | Resources are never serialized | core | works | `test_a_json_round_trip_still_produces_the_same_answer[example0_identity]`, `test_a_json_round_trip_still_produces_the_same_answer[example1_math]`, `test_a_snapshot_never_contains_a_resource`, `test_a_workflow_round_trips_through_json_without_its_resources` |

<details><summary>Notes &amp; sharp edges</summary>

- `persist.recipe_only` — `to_json` documents 'payloads excluded' but dumps list[Step], and Step embeds output.value inline — so every computed value travels.

</details>

## components

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `component.registry` | ToolRegistry works standalone | core | works | `test_a_frozen_registry_refuses_further_registration`, `test_tool_registry_alone` |
| OK | `component.resources` | ResourceContainer works standalone | core | works | `test_resource_container_alone` |
| OK | `component.data_store` | DataStore works standalone | important | works | `test_data_store_alone` |
| OK | `component.resolver` | ReferenceResolver works standalone | important | works | `test_reference_resolver_alone` |
| OK | `component.engine` | CoreEngine executes a single call | core | works | `test_core_engine_alone` |
| OK | `component.session_manager` | SessionManager hands out contexts | important | works | `test_session_manager_alone` |

<details><summary>Notes &amp; sharp edges</summary>

- `component.session_manager` — `get_or_create` is async while `get`/`discard` are not — easy to await-by-accident or forget.

</details>

## development

| | id | capability | priority | verdict | exercised by |
| --- | --- | --- | --- | --- | --- |
| OK | `dev.decorator` | `@register_tool` registers a working tool | core | works | `test_the_decorator_registers_and_returns_a_usable_tool` |
| OK | `dev.app_facade` | App → Session → Workflow works end to end | core | works | `test_the_app_facade_end_to_end`, `test_the_app_lists_its_tools_for_discovery` |
| OK | `dev.incremental` | Build and run a step at a time | core | works | `test_a_step_can_be_deleted_from_a_workflow`, `test_a_workflow_can_be_built_and_run_one_step_at_a_time` |
| OK | `dev.edit_rerun` | Replace a step and re-run it | core | works | `test_a_step_can_be_replaced_and_re_run_without_rebuilding` |
| OK | `dev.debug_one_tool` | Run one tool with no workflow at all | important | works | `test_a_single_tool_runs_with_no_workflow_engine_or_session` |
| OK | `dev.declarative` | Build a workflow from data, not Python | important | works | `test_a_workflow_can_be_built_from_json_rather_than_python` |

<details><summary>Notes &amp; sharp edges</summary>

- `dev.decorator` — Writes to the process-global REGISTRY, so a test using it must clean up or it leaks into every later test.
- `dev.edit_rerun` — `Operation` is frozen, so editing means replacing the step.

</details>
