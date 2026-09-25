# CLI reference — pipefy-pipes-and-cards

Use the shared domain workflow in `SKILL.md`; apply the following controls only on this surface.

| Operation | CLI |
|---|---|
| `get_pipe` | `pipefy pipe get <id>` |
| `search_pipes` | `pipefy pipe list` |
| `create_pipe` | `pipefy pipe create` |
| `update_pipe` | `pipefy pipe update <id>` |
| `delete_pipe` | `pipefy pipe delete <id>` |
| `clone_pipe` | `pipefy pipe clone <id>` |
| `get_pipe_members` | `pipefy member list --pipe <id>` |

CLI: `pipefy pipe create --name "Customer Onboarding" --org 123`

| Operation | CLI |
|---|---|
| `get_pipe` | `pipefy phase get <id>` |
| `create_phase` | `pipefy phase create` |
| `update_phase` | `pipefy phase update <id>` |
| `delete_phase` | `pipefy phase delete <id>` |
| `get_phase_allowed_move_targets` | `pipefy phase targets <id>` |
| `get_phase_cards_count` | `pipefy phase count <id>` |
| `get_phase_cards` | `pipefy phase cards <id>` |

| Operation | CLI |
|---|---|
| `get_pipe` | `pipefy pipe get <pipe_id>` |
| `get_phase_cards_count` | `pipefy phase count <phase_id>` |
| `create_card` | `pipefy card create <pipe_id> --phase-id <id>` |
| `get_phase_cards` | `pipefy phase cards <phase_id>` |
| `get_phase_allowed_move_targets` | `pipefy phase targets <phase_id>` |
| `move_card_to_phase` | `pipefy card move <card_id> --phase <id>` |

CLI: `pipefy pipe get 306996634 --json`

CLI: `pipefy phase count 340012345 --json`

CLI:
   ```bash
   pipefy card create 306996634 --phase-id 340012345 --title "Seeded"
   ```

CLI: `pipefy phase cards 340012345 --json`

CLI: `pipefy phase targets <current_phase_id> --json`

| Operation | CLI |
|---|---|
| `get_phase_fields` | `pipefy field list --phase <id>` |
| `get_start_form_fields` | `pipefy pipe start-form <pipe_id>` |
| `create_phase_field` | `pipefy field create --phase <id>` |
| `update_phase_field` | `pipefy field update <id>` |
| `delete_phase_field` | `pipefy field delete <id>` |

| Operation | CLI |
|---|---|
| `get_card` | `pipefy card get <id>` |
| `get_cards` | `pipefy card list --pipe <id>` |
| `find_cards` | `pipefy card find --pipe <id>` |
| `create_card` | `pipefy card create <pipe_id>` |
| `fill_card_phase_fields` | `pipefy card fill <id> --phase <id>` |
| `update_card` | `pipefy card update <id>` (`--field-updates` = `updateFieldsValues`) |
| `update_card_field` | *(MCP only; no direct CLI twin — use `card update --field-updates`)* |
| `move_card_to_phase` | `pipefy card move <card_id> --phase <id>` |
| `delete_card` | `pipefy card delete <id>` |
| `add_card_comment` | `pipefy card comment add <id>` |
| `update_comment` | `pipefy card comment update` |
| `delete_comment` | `pipefy card comment delete` |
| `upload_attachment_to_card` | `pipefy attachment upload --card` |

CLI: `pipefy pipe start-form 67890 --json`

CLI:
   ```bash
   pipefy card create 67890 --title "My Card" --fields '{"field_slug":"value"}'
   ```

| Operation | CLI |
|---|---|
| `get_labels` | `pipefy label list --pipe <id>` |
| `create_label` | `pipefy label create` |
| `update_label` | `pipefy label update <id>` |
| `delete_label` | `pipefy label delete <id>` |

| Operation | CLI |
|---|---|
| `get_field_conditions` | `pipefy field-condition list --phase <id>` |
| `get_field_condition` | `pipefy field-condition get` |
| `create_field_condition` | `pipefy field-condition create` |
| `update_field_condition` | `pipefy field-condition update` |
| `delete_field_condition` | `pipefy field-condition delete` |

## Controls and argument shapes

Destructive delete commands use `--yes`.

`pipefy phase get <id>` reads one phase. `pipefy phase cards <id>` accepts `--first`, `--after`, and optional `--include-fields`.

`pipefy card update --field-updates` accepts a JSON array for `updateFieldsValues`. `pipefy card fill --fields` takes a JSON object, filters editable IDs, and is non-interactive. Prefer `card update --field-updates` for ad-hoc updates and incremental ADD/REMOVE on list-valued fields; `update_card_field` has no direct CLI twin.

Phase moves and field-condition writes return raw GraphQL/SDK results. They do not carry MCP required-empty-field hints, required+hide rejection, or the field-condition verification envelope. Check the resulting rule and phase yourself; do not hide required fields.
