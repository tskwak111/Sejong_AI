BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT plan(26);

SELECT has_table(
  'app_private', 'citizen_feedback',
  'citizen feedback uses a private table'
);

SELECT results_eq(
  $actual$
    SELECT columns.column_name::text COLLATE "C"
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'citizen_feedback'
    ORDER BY columns.ordinal_position
  $actual$,
  $expected$
    SELECT expected.column_name COLLATE "C"
    FROM (VALUES
      ('id'::text), ('response_request_id'::text), ('rating'::text),
      ('category'::text), ('reason_code'::text), ('masked_detail'::text),
      ('detail_was_masked'::text), ('created_at'::text),
      ('detail_expires_at'::text), ('detail_purged_at'::text)
    ) AS expected(column_name)
  $expected$,
  'feedback stores only closed metadata and masked detail lifecycle'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'citizen_feedback'
      AND columns.column_name IN (
        'raw_detail', 'raw_question', 'answer_snapshot',
        'provider_body', 'context_token'
      )
  ),
  0,
  'feedback has no raw detail, transcript, answer or provider columns'
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
        'record_citizen_feedback',
        'list_citizen_feedback',
        'summarize_citizen_feedback',
        'purge_expired_citizen_feedback_detail'
      )
    ORDER BY 1
  $actual$,
  $expected$
    SELECT expected.signature COLLATE "C"
    FROM (VALUES
      ('app_api.list_citizen_feedback(p_limit integer)'::text),
      ('app_api.purge_expired_citizen_feedback_detail()'::text),
      ('app_api.record_citizen_feedback(p_response_request_id uuid, p_rating text, p_category text, p_reason_code text, p_masked_detail text, p_detail_was_masked boolean)'::text),
      ('app_api.summarize_citizen_feedback()'::text)
    ) AS expected(signature)
    ORDER BY 1
  $expected$,
  'feedback exposes exactly three fixed capabilities'
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
        'record_citizen_feedback',
        'list_citizen_feedback',
        'summarize_citizen_feedback',
        'purge_expired_citizen_feedback_detail'
      )
      AND functions.prosecdef
      AND owners.rolname = 'sejong_schema_owner'
      AND functions.proconfig = ARRAY['search_path=pg_catalog, pg_temp']::text[]
  ),
  4,
  'all feedback capabilities are owner-definer with fixed search_path'
);

SELECT ok(
  NOT pg_catalog.has_table_privilege(
    'sejong_backend', 'app_private.citizen_feedback', 'SELECT'
  )
  AND NOT pg_catalog.has_table_privilege(
    'sejong_backend', 'app_private.citizen_feedback', 'INSERT'
  )
  AND pg_catalog.has_function_privilege(
    'sejong_backend',
    'app_api.record_citizen_feedback(uuid,text,text,text,text,boolean)',
    'EXECUTE'
  )
  AND NOT pg_catalog.has_function_privilege(
    'anon',
    'app_api.record_citizen_feedback(uuid,text,text,text,text,boolean)',
    'EXECUTE'
  )
  AND NOT pg_catalog.has_function_privilege(
    'authenticated',
    'app_api.record_citizen_feedback(uuid,text,text,text,text,boolean)',
    'EXECUTE'
  ),
  'backend uses capabilities and browser roles cannot access feedback'
);

SELECT throws_ok(
  $$SELECT app_api.record_citizen_feedback(
    '81000000-0000-4000-8000-000000000001',
    'SATISFIED', 'OTHER', NULL, NULL, false
  )$$,
  'P1010', 'INVALID_CITIZEN_FEEDBACK',
  'satisfied feedback rejects dissatisfaction fields'
);

CREATE TEMPORARY TABLE feedback_cases (
  label text PRIMARY KEY,
  id uuid NOT NULL
) ON COMMIT DROP;

INSERT INTO feedback_cases (label, id)
VALUES (
  'satisfied',
  app_api.record_citizen_feedback(
    '81000000-0000-4000-8000-000000000001',
    'SATISFIED', NULL, NULL, NULL, false
  )
);

SELECT is(
  (
    SELECT feedback.rating
    FROM app_private.citizen_feedback AS feedback
    JOIN feedback_cases AS cases ON cases.id = feedback.id
    WHERE cases.label = 'satisfied'
  ),
  'SATISFIED',
  'satisfied feedback stores only its rating'
);

SELECT is(
  (
    SELECT feedback.detail_expires_at IS NULL
      AND feedback.detail_purged_at IS NULL
    FROM app_private.citizen_feedback AS feedback
    JOIN feedback_cases AS cases ON cases.id = feedback.id
    WHERE cases.label = 'satisfied'
  ),
  true,
  'satisfied feedback has no text retention lifecycle'
);

SELECT throws_ok(
  $$SELECT app_api.record_citizen_feedback(
    '81000000-0000-4000-8000-000000000002',
    'DISSATISFIED', 'OTHER', 'OTHER', NULL, false
  )$$,
  'P1010', 'INVALID_CITIZEN_FEEDBACK',
  'OTHER reason requires masked detail'
);

INSERT INTO feedback_cases (label, id)
VALUES (
  'detail',
  app_api.record_citizen_feedback(
    '81000000-0000-4000-8000-000000000002',
    'DISSATISFIED', 'OTHER', 'OTHER',
    '연락처 [전화번호]가 보여요', true
  )
);

SELECT is(
  (
    SELECT feedback.category || ':' || feedback.reason_code
      || ':' || feedback.masked_detail
    FROM app_private.citizen_feedback AS feedback
    JOIN feedback_cases AS cases ON cases.id = feedback.id
    WHERE cases.label = 'detail'
  ),
  'OTHER:OTHER:연락처 [전화번호]가 보여요',
  'only masked detail reaches the private row'
);

SELECT is(
  (
    SELECT feedback.detail_expires_at = feedback.created_at + interval '30 days'
    FROM app_private.citizen_feedback AS feedback
    JOIN feedback_cases AS cases ON cases.id = feedback.id
    WHERE cases.label = 'detail'
  ),
  true,
  'masked detail receives exact 30-day retention'
);

SELECT is(
  app_api.record_citizen_feedback(
    '81000000-0000-4000-8000-000000000002',
    'DISSATISFIED', 'OTHER', 'OTHER',
    '연락처 [전화번호]가 보여요', true
  ),
  (
    SELECT id FROM feedback_cases WHERE label = 'detail'
  ),
  'same request and payload is idempotent'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_private.citizen_feedback
  ),
  2,
  'idempotent replay creates no duplicate row'
);

SELECT throws_ok(
  $$SELECT app_api.record_citizen_feedback(
    '81000000-0000-4000-8000-000000000002',
    'DISSATISFIED', 'OTHER', 'OTHER', '다른 의견', false
  )$$,
  'P1003', 'FEEDBACK_REQUEST_CONFLICT',
  'different payload for one request is rejected'
);

SELECT throws_ok(
  $$SELECT * FROM app_api.list_citizen_feedback(101)$$,
  'P1010', 'INVALID_CITIZEN_FEEDBACK_LIMIT',
  'feedback listing rejects limits above 100'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_api.list_citizen_feedback(100)
  ),
  2,
  'admin listing returns closed feedback rows'
);

SELECT results_eq(
  $$SELECT total_count, satisfied_count, dissatisfied_count
    FROM app_api.summarize_citizen_feedback()$$,
  $$VALUES (2::integer, 1::integer, 1::integer)$$,
  'aggregate counts include every feedback row'
);

SELECT is(
  (
    SELECT category_counts = '{"OTHER": 1}'::jsonb
      AND reason_counts = '{"OTHER": 1}'::jsonb
    FROM app_api.summarize_citizen_feedback()
  ),
  true,
  'aggregate breakdown uses only closed category and reason codes'
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
      AND relations.relname = 'citizen_feedback'
      AND constraints.contype = 'f'
  ),
  0,
  'feedback cannot traverse to interaction, question or answer rows'
);

UPDATE app_private.citizen_feedback AS feedback
SET created_at = expired.reference_time - interval '31 days',
    detail_expires_at = expired.reference_time - interval '1 day'
FROM (SELECT pg_catalog.clock_timestamp() AS reference_time) AS expired
WHERE feedback.id = (
  SELECT id FROM feedback_cases WHERE label = 'detail'
);

SELECT results_eq(
  $$SELECT purged_count, purged_ids
    FROM app_api.purge_expired_citizen_feedback_detail()$$,
  $$SELECT
      1::integer,
      ARRAY[(SELECT id FROM feedback_cases WHERE label = 'detail')]::uuid[]$$,
  'purge reports exactly the expired masked detail'
);

SELECT is(
  (
    SELECT feedback.masked_detail IS NULL
      AND feedback.detail_purged_at IS NOT NULL
      AND feedback.rating = 'DISSATISFIED'
      AND feedback.category = 'OTHER'
      AND feedback.reason_code = 'OTHER'
      AND feedback.detail_was_masked
    FROM app_private.citizen_feedback AS feedback
    JOIN feedback_cases AS cases ON cases.id = feedback.id
    WHERE cases.label = 'detail'
  ),
  true,
  'purge preserves closed metadata'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_private.citizen_feedback
    WHERE masked_detail IS NOT NULL
  ),
  0,
  'no expired masked detail remains'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_private.citizen_feedback
    WHERE rating = 'SATISFIED'
  ),
  1,
  'purge keeps satisfied metadata'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_api.list_citizen_feedback(1)
  ),
  1,
  'bounded listing respects requested limit'
);

SELECT is(
  (
    SELECT detail_was_masked
    FROM app_api.list_citizen_feedback(100)
    WHERE response_request_id = '81000000-0000-4000-8000-000000000002'
  ),
  true,
  'admin listing retains only the masked-detail flag after purge'
);

SELECT * FROM finish();

ROLLBACK;
