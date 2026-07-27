BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT plan(22);

SELECT has_table(
  'app_private', 'civic_scope_gaps',
  'civic scope gaps are stored in a separate private queue'
);

SELECT results_eq(
  $actual$
    SELECT columns.column_name::text COLLATE "C"
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'civic_scope_gaps'
    ORDER BY columns.ordinal_position
  $actual$,
  $expected$
    SELECT expected.column_name COLLATE "C"
    FROM (VALUES
      ('id'::text), ('masked_question'::text), ('status'::text),
      ('created_at'::text), ('updated_at'::text),
      ('text_expires_at'::text), ('text_purged_at'::text),
      ('reviewed_by'::text), ('reviewed_at'::text),
      ('review_comment'::text)
    ) AS expected(column_name)
  $expected$,
  'scope-gap queue has only masked text, review state and lifecycle timestamps'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'civic_scope_gaps'
      AND columns.column_name IN (
        'raw_question', 'answer_snapshot', 'source_snapshot', 'context_token',
        'failed_question_id', 'candidate_id', 'kb_document_id'
      )
  ),
  0,
  'scope-gap queue has no raw transcript, answer, source or workflow link'
);

SELECT results_eq(
  $actual$
    SELECT pg_catalog.format(
      '%I.%I(%s)', namespaces.nspname, functions.proname,
      pg_catalog.pg_get_function_identity_arguments(functions.oid)
    )::text COLLATE "C"
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
      AND functions.proname IN (
        'record_civic_scope_gap', 'list_civic_scope_gaps',
        'review_civic_scope_gap', 'purge_expired_civic_scope_gap_text'
      )
    ORDER BY 1
  $actual$,
  $expected$
    SELECT expected.signature COLLATE "C"
    FROM (VALUES
      ('app_api.list_civic_scope_gaps(p_status text)'::text),
      ('app_api.purge_expired_civic_scope_gap_text()'::text),
      ('app_api.record_civic_scope_gap(p_masked_question text)'::text),
      ('app_api.review_civic_scope_gap(p_scope_gap_id uuid, p_actor_id text, p_actor_role text, p_decision text, p_review_comment text)'::text)
    ) AS expected(signature)
    ORDER BY 1
  $expected$,
  'scope-gap queue exposes exactly four fixed capabilities'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE namespaces.nspname = 'app_api'
      AND functions.proname IN (
        'record_civic_scope_gap', 'list_civic_scope_gaps',
        'review_civic_scope_gap', 'purge_expired_civic_scope_gap_text'
      )
      AND functions.prosecdef
      AND owners.rolname = 'sejong_schema_owner'
      AND functions.proconfig = ARRAY['search_path=pg_catalog, pg_temp']::text[]
  ),
  4,
  'all scope-gap capabilities are owner-definer with fixed search_path'
);

SELECT ok(
  NOT pg_catalog.has_table_privilege(
    'sejong_backend', 'app_private.civic_scope_gaps', 'SELECT'
  )
  AND NOT pg_catalog.has_table_privilege(
    'sejong_backend', 'app_private.civic_scope_gaps', 'INSERT'
  )
  AND pg_catalog.has_function_privilege(
    'sejong_backend', 'app_api.record_civic_scope_gap(text)', 'EXECUTE'
  )
  AND pg_catalog.has_function_privilege(
    'sejong_backend', 'app_api.review_civic_scope_gap(uuid,text,text,text,text)',
    'EXECUTE'
  )
  AND NOT pg_catalog.has_function_privilege(
    'anon', 'app_api.record_civic_scope_gap(text)', 'EXECUTE'
  )
  AND NOT pg_catalog.has_function_privilege(
    'authenticated', 'app_api.record_civic_scope_gap(text)', 'EXECUTE'
  ),
  'backend uses only capabilities and browser roles cannot access the queue'
);

SELECT throws_ok(
  $$SELECT app_api.record_civic_scope_gap(' ')$$,
  'P1010', 'INVALID_CIVIC_SCOPE_GAP_TEXT',
  'scope-gap recording rejects blank masked text'
);

SELECT throws_ok(
  $$SELECT app_api.record_civic_scope_gap(pg_catalog.repeat('가', 2001))$$,
  'P1010', 'INVALID_CIVIC_SCOPE_GAP_TEXT',
  'scope-gap recording rejects unbounded masked text'
);

CREATE TEMPORARY TABLE scope_gap_cases (
  label text PRIMARY KEY,
  id uuid NOT NULL
) ON COMMIT DROP;

INSERT INTO scope_gap_cases (label, id)
VALUES (
  'unexpired',
  app_api.record_civic_scope_gap('합성 범위 부족 민원 안내')
);

SELECT is(
  (
    SELECT gaps.status || ':' || gaps.masked_question
    FROM app_private.civic_scope_gaps AS gaps
    JOIN scope_gap_cases AS cases ON cases.id = gaps.id
    WHERE cases.label = 'unexpired'
  ),
  'NEW:합성 범위 부족 민원 안내',
  'recording creates one NEW row with only the supplied masked text'
);

SELECT is(
  (
    SELECT gaps.text_expires_at = gaps.created_at + interval '30 days'
    FROM app_private.civic_scope_gaps AS gaps
    JOIN scope_gap_cases AS cases ON cases.id = gaps.id
    WHERE cases.label = 'unexpired'
  ),
  true,
  'scope-gap text receives exact 30-day retention'
);

SELECT throws_ok(
  $$SELECT * FROM app_api.list_civic_scope_gaps('APPROVED')$$,
  'P1010', 'INVALID_CIVIC_SCOPE_GAP_FILTER',
  'scope-gap listing rejects unknown status filters'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_api.list_civic_scope_gaps('NEW')
  ),
  1,
  'NEW listing returns the recorded scope gap'
);

INSERT INTO app_private.civic_scope_gaps (
  id, masked_question
) VALUES (
  'c6800000-0000-4000-8000-000000000001',
  '합성 검토 대상 민원'
);

SELECT throws_ok(
  $$SELECT app_api.review_civic_scope_gap(
    'c6800000-0000-4000-8000-000000000001',
    'OPERATOR-LOCAL-001', 'OPERATOR', 'PLANNED', '검토 계획'
  )$$,
  'P1010', 'INVALID_CIVIC_SCOPE_GAP_REVIEW',
  'only an APPROVER capability may review scope gaps'
);

SELECT throws_ok(
  $$SELECT app_api.review_civic_scope_gap(
    'c6800000-0000-4000-8000-000000000001',
    'APPROVER-LOCAL-001', 'APPROVER', 'ACTIVE', '잘못된 결정'
  )$$,
  'P1010', 'INVALID_CIVIC_SCOPE_GAP_REVIEW',
  'review rejects decisions outside PLANNED or DISMISSED'
);

SELECT throws_ok(
  $$SELECT app_api.review_civic_scope_gap(
    'c6800000-0000-4000-8000-000000000001',
    'APPROVER-LOCAL-001', 'APPROVER', 'PLANNED', ' '
  )$$,
  'P1010', 'INVALID_CIVIC_SCOPE_GAP_REVIEW',
  'review requires a non-empty bounded comment'
);

SELECT lives_ok(
  $$SELECT app_api.review_civic_scope_gap(
    'c6800000-0000-4000-8000-000000000001',
    'APPROVER-LOCAL-001', 'APPROVER', 'PLANNED', '다음 범위 검토'
  )$$,
  'APPROVER can move a NEW scope gap to PLANNED'
);

SELECT is(
  (
    SELECT status = 'PLANNED'
      AND reviewed_by = 'APPROVER-LOCAL-001'
      AND reviewed_at IS NOT NULL
      AND review_comment = '다음 범위 검토'
    FROM app_private.civic_scope_gaps
    WHERE id = 'c6800000-0000-4000-8000-000000000001'
  ),
  true,
  'terminal scope-gap review stores only bounded review metadata'
);

SELECT throws_ok(
  $$SELECT app_api.review_civic_scope_gap(
    'c6800000-0000-4000-8000-000000000001',
    'APPROVER-LOCAL-002', 'APPROVER', 'DISMISSED', '재검토 금지'
  )$$,
  'P1003', 'INVALID_WORKFLOW_STATE',
  'terminal scope-gap rows cannot be reviewed twice'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_constraint AS constraints
    JOIN pg_catalog.pg_class AS relations
      ON relations.oid = constraints.conrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = relations.relnamespace
    WHERE namespaces.nspname = 'app_private'
      AND relations.relname = 'civic_scope_gaps'
      AND constraints.contype = 'f'
  ),
  0,
  'scope-gap rows have no candidate, failed-question or ACTIVE KB foreign key'
);

UPDATE app_private.civic_scope_gaps
SET created_at = expired.reference_time - interval '31 days',
    text_expires_at = expired.reference_time - interval '1 day'
FROM (SELECT pg_catalog.clock_timestamp() AS reference_time) AS expired
WHERE id = 'c6800000-0000-4000-8000-000000000001';

SELECT results_eq(
  $$SELECT purged_count, purged_ids
    FROM app_api.purge_expired_civic_scope_gap_text()$$,
  $$VALUES (
    1::integer,
    ARRAY['c6800000-0000-4000-8000-000000000001'::uuid]
  )$$,
  'purge reports exactly the expired scope-gap text'
);

SELECT is(
  (
    SELECT masked_question IS NULL
      AND text_purged_at IS NOT NULL
      AND status = 'PLANNED'
      AND reviewed_by = 'APPROVER-LOCAL-001'
    FROM app_private.civic_scope_gaps
    WHERE id = 'c6800000-0000-4000-8000-000000000001'
  ),
  true,
  'purge preserves terminal review metadata after nulling expired text'
);

SELECT is(
  (
    SELECT gaps.masked_question
    FROM app_private.civic_scope_gaps AS gaps
    JOIN scope_gap_cases AS cases ON cases.id = gaps.id
    WHERE cases.label = 'unexpired'
  ),
  '합성 범위 부족 민원 안내',
  'purge nulls only expired masked text'
);

SELECT * FROM finish();

ROLLBACK;
