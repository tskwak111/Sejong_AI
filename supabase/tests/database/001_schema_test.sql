BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT plan(35);

SELECT has_schema('app_private', 'app_private schema exists');
SELECT has_schema('app_api', 'app_api schema exists');

SELECT has_enum('app_private', 'intent_code', 'intent_code enum exists privately');
SELECT has_enum('app_private', 'answer_status', 'answer_status enum exists privately');
SELECT has_enum('app_private', 'fallback_reason', 'fallback_reason enum exists privately');
SELECT has_enum('app_private', 'kb_status', 'kb_status enum exists privately');
SELECT has_enum('app_private', 'candidate_status', 'candidate_status enum exists privately');
SELECT has_enum('app_private', 'admin_role', 'admin_role enum exists privately');
SELECT has_enum('app_private', 'data_origin', 'data_origin enum exists privately');
SELECT enums_are(
  'app_private',
  ARRAY[
    'admin_role',
    'answer_status',
    'candidate_status',
    'data_origin',
    'fallback_reason',
    'intent_code',
    'kb_status'
  ],
  'app_private contains exactly the seven domain enums'
);

SELECT has_table('app_private', 'kb_documents', 'kb_documents is private');
SELECT has_table('app_private', 'kb_question_examples', 'kb_question_examples is private');
SELECT has_table('app_private', 'offices', 'offices is private');
SELECT has_table('app_private', 'office_service_mappings', 'office mappings are private');
SELECT has_table('app_private', 'interaction_events', 'interaction events are private');
SELECT has_table('app_private', 'failed_questions', 'failed questions are private');
SELECT has_table('app_private', 'kb_candidates', 'KB candidates are private');
SELECT has_table('app_private', 'audit_logs', 'audit logs are private');
SELECT has_table(
  'app_private', 'chat_idempotency', 'chat idempotency state is private'
);
SELECT has_table(
  'app_private', 'civic_scope_gaps', 'civic scope-gap queue is private'
);
SELECT has_table(
  'app_private', 'citizen_feedback', 'citizen feedback is private'
);
SELECT tables_are(
  'app_private',
  ARRAY[
    'audit_logs',
    'chat_idempotency',
    'citizen_feedback',
    'civic_scope_gaps',
    'failed_questions',
    'interaction_events',
    'kb_candidates',
    'kb_documents',
    'kb_question_examples',
    'office_service_mappings',
    'offices'
  ],
  'app_private contains exactly the eleven approved local/private tables'
);

SELECT is(
  (
    SELECT columns.is_generated
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'offices'
      AND columns.column_name = 'is_official'
  ),
  'ALWAYS',
  'offices.is_official is generated and not caller-writable'
);
SELECT ok(
  (
    SELECT columns.generation_expression IS NOT NULL
      AND columns.generation_expression LIKE '%data_origin%'
      AND columns.generation_expression LIKE '%OFFICIAL%'
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'offices'
      AND columns.column_name = 'is_official'
  ),
  'offices.is_official derives from OFFICIAL data_origin'
);

SELECT has_column('app_private', 'kb_documents', 'data_origin', 'KB origin exists');
SELECT col_not_null('app_private', 'kb_documents', 'data_origin', 'KB origin is required');
SELECT col_hasnt_default('app_private', 'kb_documents', 'data_origin', 'KB origin has no default');
SELECT has_column('app_private', 'offices', 'data_origin', 'office origin exists');
SELECT col_not_null('app_private', 'offices', 'data_origin', 'office origin is required');
SELECT col_hasnt_default('app_private', 'offices', 'data_origin', 'office origin has no default');
SELECT has_column('app_private', 'kb_candidates', 'data_origin', 'candidate origin exists');
SELECT col_not_null('app_private', 'kb_candidates', 'data_origin', 'candidate origin is required');
SELECT col_hasnt_default('app_private', 'kb_candidates', 'data_origin', 'candidate origin has no default');

SELECT is(
  (
    SELECT count(*)::integer
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = ANY (
        ARRAY[
          'kb_documents',
          'kb_question_examples',
          'offices',
          'office_service_mappings',
          'interaction_events',
          'failed_questions',
          'kb_candidates',
          'audit_logs',
          'chat_idempotency',
          'citizen_feedback',
          'civic_scope_gaps'
        ]
      )
      AND lower(columns.column_name) ~ '^(raw_question|question_text|answer_text|transcript|context_token|ip_address|device_id|secret|provider_payload)$'
  ),
  0,
  'private tables contain no forbidden privacy columns'
);
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_catalog.pg_namespace AS namespaces
    WHERE namespaces.nspname = 'public'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_class AS tables
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = tables.relnamespace
    WHERE namespaces.nspname = 'public'
      AND tables.relkind = ANY (ARRAY['r', 'p', 'f']::"char"[])
      AND tables.relname = ANY (
        ARRAY[
          'kb_documents',
          'kb_question_examples',
          'offices',
          'office_service_mappings',
          'interaction_events',
          'failed_questions',
          'kb_candidates',
          'audit_logs',
          'chat_idempotency',
          'citizen_feedback',
          'civic_scope_gaps'
        ]
      )
  ),
  'public contains none of the eleven approved local/private tables'
);

SELECT * FROM finish();

ROLLBACK;
