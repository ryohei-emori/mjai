## 1. Migration Script

- [x] 1.1 Create `backend/scripts/` directory if not exists
- [x] 1.2 Create `backend/scripts/migrate_sqlite_to_supabase.py` with dry-run/apply modes
- [x] 1.3 Implement SQLite読み込み (PascalCaseテーブル)
- [x] 1.4 Implement Supabase upsert (ON CONFLICT DO NOTHING)
- [x] 1.5 Handle FK順序 (sessions → histories → proposals)
- [x] 1.6 Handle 無効参照スキップとログ出力

## 2. Migration Execution

- [x] 2.1 Run dry-run mode to verify differences
- [x] 2.2 Run apply mode to migrate missing data (N/A - no missing data)
- [x] 2.3 Verify final row counts match expected

## 3. Documentation

- [x] 3.1 Add migration completion note to AGENTS.md (if any data was migrated)
  - Result: No data was migrated - Supabase already contains all valid data from SQLite
