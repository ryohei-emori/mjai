## Context

See proposal.md for motivation. The codebase maintains parallel database paths: PostgreSQL (snake_case columns, `USE_POSTGRESQL=true` default) and SQLite (camelCase columns, `USE_POSTGRESQL=false`). The `db_helper.py` module implements both paths with separate functions (e.g., `fetch_session()` vs `fetch_session_sqlite()`).

Key constraints:
- Frontend and API responses expect camelCase keys
- PostgreSQL schema uses snake_case columns (per SQL conventions)
- SQLite schema uses camelCase columns (matching the application model)
- Some PostgreSQL functions (`fetch_sessions()`) already apply column aliases; others (`fetch_session()`) do not
- The PostgreSQL `ai_proposals` table has a thin legacy schema (`proposal_text`, `confidence_score`) that doesn't match the application's full proposal model

## Goals / Non-Goals

**Goals:**
- Fix the three known PostgreSQL path bugs without breaking SQLite path
- Maintain backward compatibility with existing data
- Add test coverage to prevent regression

**Non-Goals:**
- Unifying the dual-database architecture (that's a larger refactor)
- Changing the API contract or response shapes
- Migrating existing `ai_proposals` data (new columns will be NULL for old rows)

## Decisions

### Decision 1: Apply column aliasing in `fetch_session()`

**Choice**: Add column aliases to the SQL query, matching the pattern used in `fetch_sessions()`.

**Rationale**: This is the simplest, most consistent approach. The `fetch_sessions()` function already demonstrates this pattern works correctly. Using aliases in the query avoids post-fetch transformation overhead.

**Alternative considered**: Post-fetch dict transformation (iterate rows and remap keys). Rejected because it adds code complexity and is less efficient than SQL aliases.

### Decision 2: Normalize field names in `update_session()`

**Choice**: Create a field name mapping dict and normalize incoming camelCase keys to snake_case before checking the allow-list.

```python
FIELD_MAP = {
    'correctionCount': 'correction_count',
    'isOpen': 'is_open',
    'updatedAt': 'updated_at',
}
```

**Rationale**: This approach handles both camelCase (from clients) and snake_case (direct API calls) without duplicating the allow-list. The mapping is explicit and easy to maintain.

**Alternative considered**: Duplicating allowed fields list with both casings. Rejected because it's error-prone and harder to maintain.

### Decision 3: Migrate PostgreSQL `ai_proposals` schema to full model

**Choice**: Add a new migration (`003_align_ai_proposals_schema.sql`) that adds the missing columns to match the SQLite schema. Keep legacy columns (`proposal_text`, `confidence_score`) as nullable for backward compatibility.

New columns:
- `type TEXT NOT NULL DEFAULT 'AI'`
- `original_after_text TEXT`
- `original_reason TEXT`
- `modified_after_text TEXT`
- `modified_reason TEXT`
- `is_selected INTEGER DEFAULT 0`
- `is_modified INTEGER DEFAULT 0`
- `is_custom INTEGER DEFAULT 0`
- `selected_order INTEGER`

**Rationale**: The SQLite schema represents the application's actual data model. Aligning PostgreSQL to match it ensures feature parity and simplifies the db_helper code.

**Alternative considered**: Adapting the application to the thin PostgreSQL schema. Rejected because it would remove functionality (selection tracking, modification flags, etc.) that the frontend depends on.

### Decision 4: Update `insert_proposal()` and `fetch_proposals_by_history()` with key mapping

**Choice**: Map camelCase keys from the application to snake_case columns in inserts, and apply column aliases in fetch queries (similar to session functions).

**Rationale**: Consistent with the pattern established for session functions. Keeps the mapping explicit in db_helper rather than scattered across main.py.

## Risks / Trade-offs

**[Risk] Existing `ai_proposals` rows have NULL values for new columns**
→ Mitigation: New columns have defaults (`type` defaults to `'AI'`, boolean flags default to `0`). Existing rows won't break queries, but may display incomplete data if retrieved. This is acceptable since the PostgreSQL path was broken anyway (no proposals could be created).

**[Risk] Migration must be applied before deploying code**
→ Mitigation: Document the manual migration step clearly. The code will fail gracefully (column not found) if migration isn't applied, which is the same failure mode as before the fix.

**[Trade-off] Keeping legacy columns adds schema bloat**
→ Accepted: The columns are small (TEXT, REAL) and removing them would require a data migration. They can be dropped in a future cleanup change.

## Migration Plan

1. **Pre-deployment**: Owner applies `003_align_ai_proposals_schema.sql` to Render Postgres
2. **Deployment**: Deploy updated `db_helper.py` with fixed functions
3. **Verification**: Test GET/PUT sessions and POST proposals against production
4. **Rollback**: If issues occur, the old code still works with the new schema (new columns are ignored)
