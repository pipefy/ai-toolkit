# MCP tools and CLI parity

This matrix is the source of truth for **MCP tool ↔ `pipefy` CLI** coverage. Update it whenever MCP tools or CLI commands are added, renamed, or removed.

**Registry source:** `PIPEFY_TOOL_NAMES` in `packages/mcp/src/pipefy_mcp/tools/registry.py`. `tests/test_parity.py` fails when a registered tool has no row, a row names an unregistered tool, or a shipped row names a CLI command that does not exist.

## Response shape (MCP envelope vs CLI JSON)

Many read-only MCP tools return a unified envelope (`success`, `data`, optional `message` / `pagination`) when `PIPEFY_MCP_UNIFIED_ENVELOPE` is true (default). The CLI prints the **underlying SDK/GraphQL payload** with `--json` — there is no `success` wrapper. When comparing the same capability on both surfaces, diff the **core fields** (`pipe`, `card`, `organizations`, …); on MCP they usually live under **`data`**.

For **database records**, `find_records` result nodes may use **`fields`** while list/get table record responses may use **`record_fields`** — that follows Pipefy’s GraphQL shape per operation, not an MCP vs CLI inconsistency.

## Status legend

| Status | Meaning |
| --- | --- |
| **shipped** | CLI command exists in `packages/cli` today. |
| **pending** | Planned CLI coverage not shipped yet (see matrix). |
| **deferred** | Not targeted for the initial CLI parity wave; see **Notes**. |
| **N/A** | MCP- or IDE-oriented surface with no first-class CLI twin planned. |

MCP destructive tools use a two-step `confirmation_token` (see [Destructive operations](mcp/tools/cross-cutting.md#destructive-operations)). A one-shot MCP `confirm=true` without that token still previews. CLI deletes confirm with `--yes` (or an interactive prompt). `unpublish_sub_portal` is ungated.

## Parity matrix

| MCP tool name | CLI command (or target) | Status | Notes |
| --- | --- | --- | --- |
| `add_card_comment` | `pipefy card comment add` | shipped | — |
| `add_service_account_to_pipe` | `pipefy member add-service-account` | shipped | MCP verifies the membership afterwards and fails when the account is absent. The CLI returns the raw invite result, so inspect `inviteMembers.errors`. |
| `call_ipaas_tool` | — | deferred | MCP-first. A CLI twin waits until agent usage settles. |
| `clone_pipe` | `pipefy pipe clone` | shipped | — |
| `create_ai_agent` | `pipefy agent create` | shipped | — |
| `create_ai_automation` | `pipefy ai-automation create` | shipped | — |
| `create_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup create` | shipped | The CLI gates on the read-access probe. |
| `create_ai_knowledge_base_document` | `pipefy kb document create` | shipped | The CLI gates on the read-access probe. |
| `create_ai_knowledge_base_plain_text` | `pipefy kb plain-text create` | shipped | The CLI gates on the read-access probe. |
| `create_attachment_presigned_url` | `pipefy attachment presign` | shipped | — |
| `create_automation` | `pipefy automation create` | shipped | — |
| `create_card` | `pipefy card create` | shipped | — |
| `create_card_relation` | `pipefy relation card create` | shipped | — |
| `create_field_condition` | `pipefy field-condition create` | shipped | MCP re-reads the condition and rejects `hide` on a required field before the mutation. The CLI returns the raw SDK response without those checks. |
| `create_ipaas_connection` | — | deferred | MCP-first. A CLI twin waits for the other iPaaS tools. |
| `create_label` | `pipefy label create` | shipped | — |
| `create_llm_provider` | `pipefy ai-provider create` | shipped | The CLI reads the configuration from a local JSON file (`--config-file`) only. |
| `create_organization_report` | `pipefy report-org create` | shipped | — |
| `create_phase` | `pipefy phase create` | shipped | — |
| `create_phase_field` | `pipefy field create` | shipped | — |
| `create_pipe` | `pipefy pipe create` | shipped | — |
| `create_pipe_relation` | `pipefy relation pipe create` | shipped | — |
| `create_pipe_report` | `pipefy report-pipe create` | shipped | — |
| `create_portal` | `pipefy portal create` | shipped | — |
| `create_portal_page` | `pipefy portal page create` | shipped | — |
| `create_portal_element` | `pipefy portal element create` | shipped | — |
| `create_sub_portal` | `pipefy portal sub-portal create` | shipped | — |
| `create_send_task_automation` | `pipefy automation send-task create` | shipped | — |
| `create_service_account` | `pipefy service-account create` | shipped | — |
| `create_table` | `pipefy table create` | shipped | — |
| `create_table_field` | `pipefy table field create` | shipped | — |
| `create_table_record` | `pipefy record create` | shipped | — |
| `create_webhook` | `pipefy webhook create` | shipped | — |
| `delete_ai_agent` | `pipefy agent delete` | shipped | — |
| `delete_ai_automation` | `pipefy ai-automation delete` | shipped | — |
| `delete_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup delete` | shipped | — |
| `delete_ai_knowledge_base_document` | `pipefy kb document delete` | shipped | — |
| `delete_ai_knowledge_base_plain_text` | `pipefy kb plain-text delete` | shipped | — |
| `delete_automation` | `pipefy automation delete` | shipped | — |
| `delete_card` | `pipefy card delete` | shipped | — |
| `delete_card_relation` | `pipefy relation card delete` | shipped | — |
| `delete_comment` | `pipefy card comment delete` | shipped | — |
| `delete_field_condition` | `pipefy field-condition delete` | shipped | — |
| `delete_label` | `pipefy label delete` | shipped | — |
| `delete_llm_provider` | `pipefy ai-provider delete` | shipped | — |
| `delete_organization_report` | `pipefy report-org delete` | shipped | — |
| `delete_phase` | `pipefy phase delete` | shipped | — |
| `delete_phase_field` | `pipefy field delete` | shipped | — |
| `delete_pipe` | `pipefy pipe delete` | shipped | — |
| `delete_pipe_relation` | `pipefy relation pipe delete` | shipped | — |
| `delete_pipe_report` | `pipefy report-pipe delete` | shipped | — |
| `delete_portal` | `pipefy portal delete` | shipped | — |
| `delete_portal_page` | `pipefy portal page delete` | shipped | — |
| `delete_portal_element` | `pipefy portal element delete` | shipped | — |
| `delete_service_account` | `pipefy service-account delete` | shipped | — |
| `delete_sub_portal` | `pipefy portal sub-portal delete` | shipped | — |
| `delete_sub_portal_element` | `pipefy portal sub-portal detach` | shipped | — |
| `delete_table` | `pipefy table delete` | shipped | — |
| `delete_table_field` | `pipefy table field delete` | shipped | — |
| `delete_table_record` | `pipefy record delete` | shipped | — |
| `delete_webhook` | `pipefy webhook delete` | shipped | — |
| `duplicate_portal_element` | `pipefy portal element duplicate` | shipped | — |
| `execute_graphql` | `pipefy graphql exec` | shipped | MCP gates mutations only, and queries run at once. A CLI mutation exits 2 without `--yes`. |
| `export_automation_jobs` | `pipefy export automation-jobs` (also `pipefy automation export jobs`) | shipped | — |
| `export_organization_report` | `pipefy report-org export` | shipped | — |
| `export_pipe_audit_logs` | `pipefy audit export` | shipped | — |
| `export_pipe_report` | `pipefy report-pipe export` | shipped | — |
| `fill_card_phase_fields` | `pipefy card fill` | shipped | — |
| `find_cards` | `pipefy card find` | shipped | — |
| `find_records` | `pipefy record find` | shipped | The MCP envelope's `pagination` uses `has_more`, `end_cursor` and `page_size`. |
| `get_agents_usage` | `pipefy usage agents` | shipped | — |
| `get_ai_agent` | `pipefy agent get` | shipped | — |
| `get_ai_agent_log_details` | `pipefy agent logs get` | shipped | — |
| `get_ai_agent_logs` | `pipefy agent logs list` | shipped | — |
| `get_ai_agents` | `pipefy agent list` | shipped | — |
| `get_ai_automation` | `pipefy ai-automation get` | shipped | — |
| `get_ai_automations` | `pipefy ai-automation list` | shipped | — |
| `get_ai_credit_usage` | `pipefy usage credits` | shipped | — |
| `get_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup get` | shipped | — |
| `get_ai_knowledge_base_document` | `pipefy kb document get` | shipped | — |
| `get_ai_knowledge_base_plain_text` | `pipefy kb plain-text get` | shipped | — |
| `get_ai_knowledge_bases` | `pipefy kb list` | shipped | — |
| `get_automation` | `pipefy automation get` | shipped | — |
| `get_automation_actions` | `pipefy automation actions list` | shipped | — |
| `get_automation_event_attributes` | `pipefy automation event-attributes` | shipped | — |
| `get_automation_execution_metrics` | `pipefy usage execution-metrics` | shipped | — |
| `get_automation_events` | `pipefy automation events list` | shipped | — |
| `get_automation_jobs_export` | `pipefy automation export status` | shipped | — |
| `get_automation_jobs_export_csv` | `pipefy export automation-jobs-csv` (also `pipefy automation export csv`) | shipped | — |
| `get_automation_logs` | `pipefy automation logs --automation` | shipped | — |
| `get_automation_logs_by_repo` | `pipefy automation logs --repo` | shipped | — |
| `get_automations` | `pipefy automation list` | shipped | — |
| `get_automations_usage` | `pipefy usage automations` (also `pipefy automation usage`) | shipped | — |
| `get_available_ai_models` | `pipefy ai-provider models` | shipped | — |
| `get_card` | `pipefy card get` | shipped | — |
| `get_card_inbox_emails` | `pipefy email inbox list` | shipped | — |
| `get_card_relations` | `pipefy relation card list` | shipped | — |
| `get_cards` | `pipefy card list` | shipped | — |
| `get_default_llm_provider` | `pipefy ai-provider default get` | shipped | — |
| `get_email_templates` | `pipefy email template list` | shipped | — |
| `get_ipaas_connection_auth_url` | — | deferred | MCP-first. A CLI twin waits for the other iPaaS tools. |
| `get_field_condition` | `pipefy field-condition get` | shipped | — |
| `get_field_conditions` | `pipefy field-condition list` | shipped | — |
| `get_ipaas_tools` | — | deferred | MCP-first. A CLI twin waits for the other iPaaS tools. |
| `get_labels` | `pipefy label list` | shipped | — |
| `get_llm_provider_dependencies` | `pipefy ai-provider dependencies` | shipped | — |
| `get_llm_providers` | `pipefy ai-provider list` | shipped | — |
| `get_organization` | `pipefy org get` | shipped | — |
| `get_organization_report` | `pipefy report-org get` | shipped | — |
| `get_organization_report_export` | (poll via `pipefy report-org export --format json`) | shipped | — |
| `get_organization_reports` | `pipefy report-org list` | shipped | — |
| `get_phase_allowed_move_targets` | `pipefy phase targets` | shipped | — |
| `get_phase_cards` | `pipefy phase cards` | shipped | — |
| `get_phase_cards_count` | `pipefy phase count` | shipped | — |
| `get_phase_fields` | `pipefy field list --phase` | shipped | — |
| `get_pipe` | `pipefy pipe get` | shipped | — |
| `get_pipe_members` | `pipefy member list` | shipped | — |
| `get_pipe_relations` | `pipefy relation pipe list` | shipped | — |
| `get_pipe_report` | `pipefy report-pipe get` | shipped | — |
| `get_pipe_report_columns` | `pipefy report-pipe columns` | shipped | — |
| `get_pipe_report_export` | (poll via `pipefy report-pipe export --format json`) | shipped | — |
| `get_pipe_report_filterable_fields` | `pipefy report-pipe filterable-fields` | shipped | — |
| `get_pipe_reports` | `pipefy report-pipe list` | shipped | — |
| `get_portal` | `pipefy portal get` | shipped | — |
| `get_start_form_fields` | `pipefy pipe start-form` | shipped | — |
| `get_table` | `pipefy table get` | shipped | — |
| `get_table_record` | `pipefy record get` | shipped | — |
| `get_table_records` | `pipefy record find` | shipped | Omit `field_id` and `field_value` in `--filter`. |
| `get_table_relations` | `pipefy relation table list` | shipped | — |
| `get_tables` | `pipefy table list --ids` | shipped | — |
| `get_webhooks` | `pipefy webhook list` | shipped | — |
| `introspect_mutation` | `pipefy introspect mutation` | shipped | — |
| `introspect_query` | `pipefy introspect query` | shipped | — |
| `introspect_type` | `pipefy introspect type` | shipped | — |
| `invite_members` | `pipefy member invite` | shipped | — |
| `list_organizations` | `pipefy org list` | shipped | — |
| `list_portals` | `pipefy portal list` | shipped | — |
| `move_card_to_phase` | `pipefy card move` | shipped | On a required-field failure, MCP names the field. The CLI returns the raw GraphQL error. |
| `publish_sub_portal` | `pipefy portal sub-portal publish` | shipped | — |
| `remove_member_from_pipe` | `pipefy member remove` | shipped | — |
| `reset_default_llm_provider` | `pipefy ai-provider default reset` | shipped | — |
| `search_pipes` | `pipefy pipe list` | shipped | — |
| `search_schema` | `pipefy introspect schema search` | shipped | — |
| `search_tables` | `pipefy table list` | shipped | — |
| `send_email_with_template` | `pipefy email template send` | shipped | The CLI prints the email and exits 2 without `--yes`. |
| `send_inbox_email` | `pipefy email inbox send` | shipped | The CLI prints the email and exits 2 without `--yes`. |
| `set_default_llm_provider` | `pipefy ai-provider default set` | shipped | — |
| `set_llm_provider_active_status` | `pipefy ai-provider set-active-status` | shipped | — |
| `set_role` | `pipefy member set-role` | shipped | — |
| `set_table_record_field_value` | `pipefy record update` | shipped | — |
| `simulate_automation` | `pipefy automation simulate` | shipped | — |
| `sort_portal_pages` | `pipefy portal page sort` | shipped | — |
| `toggle_ai_agent_status` | `pipefy agent toggle` | shipped | — |
| `unpublish_sub_portal` | `pipefy portal sub-portal unpublish` | shipped | — |
| `update_ai_agent` | `pipefy agent update` | shipped | — |
| `update_ai_automation` | `pipefy ai-automation update` | shipped | — |
| `update_ai_knowledge_base_data_lookup` | `pipefy kb data-lookup update` | shipped | The CLI gates on the read-access probe. |
| `update_ai_knowledge_base_document` | `pipefy kb document update` | shipped | The CLI gates on the read-access probe. |
| `update_ai_knowledge_base_plain_text` | `pipefy kb plain-text update` | shipped | The CLI gates on the read-access probe. |
| `update_automation` | `pipefy automation update` | shipped | — |
| `update_card` | `pipefy card update` | shipped | — |
| `update_card_field` | — | N/A | MCP only. Use `pipefy card update --field-updates` instead. |
| `update_comment` | `pipefy card comment update` | shipped | — |
| `update_field_condition` | `pipefy field-condition update` | shipped | MCP rejects `hide` on a required field before the mutation. The CLI returns the raw SDK response without that check. |
| `update_label` | `pipefy label update` | shipped | — |
| `update_llm_provider` | `pipefy ai-provider update` | shipped | The CLI reads the configuration from a local JSON file only. |
| `update_organization_report` | `pipefy report-org update` | shipped | — |
| `update_phase` | `pipefy phase update` | shipped | — |
| `update_phase_field` | `pipefy field update` | shipped | — |
| `update_pipe` | `pipefy pipe update` | shipped | — |
| `update_pipe_relation` | `pipefy relation pipe update` | shipped | — |
| `update_pipe_report` | `pipefy report-pipe update` | shipped | — |
| `update_portal` | `pipefy portal update` | shipped | — |
| `update_portal_page` | `pipefy portal page update` | shipped | — |
| `update_portal_page_layout` | `pipefy portal page layout update` | shipped | — |
| `update_portal_element` | `pipefy portal element update` | shipped | — |
| `update_sub_portal_element` | `pipefy portal sub-portal attach` | shipped | — |
| `update_table` | `pipefy table update` | shipped | — |
| `update_table_field` | `pipefy table field update` | shipped | — |
| `update_table_record` | `pipefy record update` | shipped | — |
| `update_webhook` | `pipefy webhook update` | shipped | — |
| `upload_attachment_to_card` | `pipefy attachment upload --card` | shipped | MCP also accepts `file_url`, and the hosted profile rejects `file_path`. The CLI takes a local `--file` only. |
| `upload_attachment_to_table_record` | `pipefy attachment upload --record` | shipped | MCP also accepts `file_url`, and the hosted profile rejects `file_path`. The CLI takes a local `--file` only. |
| `validate_ai_agent_behaviors` | `pipefy agent validate-behaviors` | shipped | — |
| `validate_ai_automation_prompt` | `pipefy ai-automation validate-prompt` | shipped | — |
| `validate_knowledge_base_access` | `pipefy kb validate-access` | shipped | — |
| `validate_llm_provider_access` | `pipefy ai-provider validate-access` | shipped | — |

