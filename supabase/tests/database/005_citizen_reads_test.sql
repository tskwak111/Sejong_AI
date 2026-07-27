BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT no_plan();

-- Exact identities, return records, stability, ownership, fixed search path,
-- and the absence of overloads are part of the backend-only DB contract.
SELECT results_eq(
  $actual$
    SELECT functions.proname::text COLLATE "C",
      pg_catalog.pg_get_function_identity_arguments(functions.oid)::text
        COLLATE "C"
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
      AND functions.proname IN ('list_active_kb', 'list_offices')
    ORDER BY functions.proname COLLATE "C"
  $actual$,
  $expected$
    SELECT expected.function_name COLLATE "C",
      expected.identity_arguments COLLATE "C"
    FROM (
      VALUES
        ('list_active_kb'::text, 'p_intent text'::text),
        ('list_offices'::text, 'p_region text, p_intent text'::text)
    ) AS expected(function_name, identity_arguments)
  $expected$,
  'citizen reads expose only the two exact argument identities'
);

SELECT is(
  COALESCE(
    (
      SELECT pg_catalog.pg_get_function_result(functions.oid)
      FROM pg_catalog.pg_proc AS functions
      JOIN pg_catalog.pg_namespace AS namespaces
        ON namespaces.oid = functions.pronamespace
      WHERE namespaces.nspname = 'app_api'
        AND functions.proname = 'list_active_kb'
        AND pg_catalog.pg_get_function_identity_arguments(functions.oid) =
          'p_intent text'
    ),
    ''
  ),
  'TABLE(public_id text, category text, service_name text, answer_summary text, procedure_steps jsonb, required_documents jsonb, processing_time text, fee text, department text, source_title text, source_url text, last_verified_at date, caution text, question_examples jsonb)',
  'list_active_kb returns the exact public record shape'
);

SELECT is(
  COALESCE(
    (
      SELECT pg_catalog.pg_get_function_result(functions.oid)
      FROM pg_catalog.pg_proc AS functions
      JOIN pg_catalog.pg_namespace AS namespaces
        ON namespaces.oid = functions.pronamespace
      WHERE namespaces.nspname = 'app_api'
        AND functions.proname = 'list_offices'
        AND pg_catalog.pg_get_function_identity_arguments(functions.oid) =
          'p_region text, p_intent text'
    ),
    ''
  ),
  'TABLE(public_id text, region text, office_name text, address text, phone text, opening_hours text, map_url text, department_label text, source_title text, source_url text, last_verified_at date)',
  'list_offices returns the exact public record shape'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE namespaces.nspname = 'app_api'
      AND functions.proname IN ('list_active_kb', 'list_offices')
      AND functions.provolatile = 's'
      AND functions.prosecdef
      AND owners.rolname = 'sejong_schema_owner'
      AND functions.proconfig =
        ARRAY['search_path=pg_catalog, pg_temp']::text[]
  ),
  2,
  'citizen reads are STABLE owner SECURITY DEFINER with fixed search_path'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    CROSS JOIN LATERAL pg_catalog.aclexplode(
      COALESCE(functions.proacl, pg_catalog.acldefault('f', functions.proowner))
    ) AS privileges
    WHERE namespaces.nspname = 'app_api'
      AND functions.proname IN ('list_active_kb', 'list_offices')
      AND privileges.grantee = 0
      AND privileges.privilege_type = 'EXECUTE'
  ),
  0,
  'citizen reads grant no effective PUBLIC execute'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
      AND functions.proname IN ('list_active_kb', 'list_offices')
      AND NOT pg_catalog.has_function_privilege(
        'anon', functions.oid, 'EXECUTE'
      )
      AND NOT pg_catalog.has_function_privilege(
        'authenticated', functions.oid, 'EXECUTE'
      )
      AND pg_catalog.has_function_privilege(
        'sejong_backend', functions.oid, 'EXECUTE'
      )
  ),
  2,
  'anon and authenticated cannot execute while backend can'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
      AND (
        (
          functions.proname = 'list_active_kb'
          AND pg_catalog.pg_get_function_identity_arguments(functions.oid) =
            'p_intent text'
        )
        OR (
          functions.proname = 'list_offices'
          AND pg_catalog.pg_get_function_identity_arguments(functions.oid) =
            'p_region text, p_intent text'
        )
      )
      AND pg_catalog.pg_get_functiondef(functions.oid)
        !~* '(^|[^[:alnum:]_])execute([^[:alnum:]_]|$)'
  ),
  2,
  'both exact citizen reads contain no standalone EXECUTE token'
);

-- Exact five ordinary indexes: names, tables, ordered key columns/direction,
-- predicates, validity/readiness, and no extra non-constraint index.
SELECT results_eq(
  $actual$
    SELECT index_rel.relname::text,
      table_rel.relname::text,
      pg_catalog.string_agg(
        attributes.attname::text ||
        CASE
          WHEN (indexes.indoption[keys.ordinality - 1] & 1) = 1
            THEN ' DESC'
          ELSE ' ASC'
        END,
        ',' ORDER BY keys.ordinality
      )::text
    FROM pg_catalog.pg_index AS indexes
    JOIN pg_catalog.pg_class AS index_rel
      ON index_rel.oid = indexes.indexrelid
    JOIN pg_catalog.pg_class AS table_rel
      ON table_rel.oid = indexes.indrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = table_rel.relnamespace
    CROSS JOIN LATERAL pg_catalog.unnest(indexes.indkey::smallint[])
      WITH ORDINALITY AS keys(attnum, ordinality)
    JOIN pg_catalog.pg_attribute AS attributes
      ON attributes.attrelid = table_rel.oid
      AND attributes.attnum = keys.attnum
    WHERE namespaces.nspname = 'app_private'
      AND index_rel.relname IN (
        'idx_kb_active_official_category', 'idx_events_occurred',
        'idx_failures_status', 'idx_failure_text_expiry',
        'idx_candidates_status'
      )
    GROUP BY index_rel.relname, table_rel.relname
    ORDER BY index_rel.relname COLLATE "C"
  $actual$,
  $expected$
    SELECT expected.index_name COLLATE "C",
      expected.table_name COLLATE "C",
      expected.key_spec COLLATE "C"
    FROM (
      VALUES
        ('idx_candidates_status'::text, 'kb_candidates'::text,
         'review_status ASC'::text),
        ('idx_events_occurred'::text, 'interaction_events'::text,
         'occurred_at DESC'::text),
        ('idx_failure_text_expiry'::text, 'failed_questions'::text,
         'text_expires_at ASC'::text),
        ('idx_failures_status'::text, 'failed_questions'::text,
         'status ASC,fallback_reason ASC'::text),
        ('idx_kb_active_official_category'::text, 'kb_documents'::text,
         'category ASC'::text)
    ) AS expected(index_name, table_name, key_spec)
  $expected$,
  'Task 7 indexes use exact tables and ordered key directions'
);

SELECT results_eq(
  $actual$
    SELECT index_rel.relname::text,
      COALESCE(
        pg_catalog.pg_get_expr(indexes.indpred, indexes.indrelid),
        ''
      )::text
    FROM pg_catalog.pg_index AS indexes
    JOIN pg_catalog.pg_class AS index_rel
      ON index_rel.oid = indexes.indexrelid
    JOIN pg_catalog.pg_class AS table_rel
      ON table_rel.oid = indexes.indrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = table_rel.relnamespace
    WHERE namespaces.nspname = 'app_private'
      AND index_rel.relname IN (
        'idx_kb_active_official_category', 'idx_events_occurred',
        'idx_failures_status', 'idx_failure_text_expiry',
        'idx_candidates_status'
      )
    ORDER BY index_rel.relname COLLATE "C"
  $actual$,
  $expected$
    SELECT expected.index_name COLLATE "C",
      expected.predicate COLLATE "C"
    FROM (
      VALUES
        ('idx_candidates_status'::text, ''::text),
        ('idx_events_occurred'::text, ''::text),
        ('idx_failure_text_expiry'::text,
         '(masked_question IS NOT NULL)'::text),
        ('idx_failures_status'::text, ''::text),
        ('idx_kb_active_official_category'::text,
         '((status = ''ACTIVE''::app_private.kb_status) AND (data_origin = ''OFFICIAL''::app_private.data_origin))'::text)
    ) AS expected(index_name, predicate)
  $expected$,
  'Task 7 indexes use exact partial predicates and no others'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_index AS indexes
    JOIN pg_catalog.pg_class AS index_rel
      ON index_rel.oid = indexes.indexrelid
    JOIN pg_catalog.pg_class AS table_rel
      ON table_rel.oid = indexes.indrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = table_rel.relnamespace
    WHERE namespaces.nspname = 'app_private'
      AND index_rel.relname IN (
        'idx_kb_active_official_category', 'idx_events_occurred',
        'idx_failures_status', 'idx_failure_text_expiry',
        'idx_candidates_status'
      )
      AND indexes.indisvalid
      AND indexes.indisready
  ),
  5,
  'all five Task 7 indexes are valid and ready'
);

SELECT results_eq(
  $actual$
    SELECT index_rel.relname::text COLLATE "C"
    FROM pg_catalog.pg_index AS indexes
    JOIN pg_catalog.pg_class AS index_rel
      ON index_rel.oid = indexes.indexrelid
    JOIN pg_catalog.pg_class AS table_rel
      ON table_rel.oid = indexes.indrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = table_rel.relnamespace
    LEFT JOIN pg_catalog.pg_constraint AS constraints
      ON constraints.conindid = indexes.indexrelid
    WHERE namespaces.nspname = 'app_private'
      AND table_rel.relname IN (
        'kb_documents', 'interaction_events', 'failed_questions',
        'kb_candidates'
      )
      AND constraints.oid IS NULL
    ORDER BY index_rel.relname COLLATE "C"
  $actual$,
  $expected$
    SELECT expected.index_name COLLATE "C"
    FROM pg_catalog.unnest(ARRAY[
      'idx_candidates_status', 'idx_events_occurred',
      'idx_failure_text_expiry', 'idx_failures_status',
      'idx_kb_active_official_category'
    ]) AS expected(index_name)
    ORDER BY expected.index_name COLLATE "C"
  $expected$,
  'approved five-name set has no missing or extra ordinary index'
);

-- Synthetic transaction-scoped fixtures. Dropping the ACTIVE/OFFICIAL check
-- only inside this rolled-back test allows defense-in-depth proof that the read
-- function itself filters an otherwise impossible ACTIVE MOCK row.
ALTER TABLE app_private.kb_documents
  DROP CONSTRAINT kb_documents_active_official_approval_chk;

INSERT INTO app_private.kb_documents (
  id, public_id, data_origin, category, service_name, answer_summary,
  procedure_steps, required_documents, processing_time, fee, department,
  source_title, source_url, last_verified_at, caution, status, created_by,
  approved_by, approved_at
) VALUES
  ('70000000-0000-4000-8000-000000000002', 'T7-KB-002', 'OFFICIAL',
   'BULKY_WASTE', 'Synthetic service 002', 'Synthetic summary 002',
   '["step 002"]', '["document 002"]', '2 days', '200 won',
   'Synthetic department 002', 'Synthetic official source 002',
   'https://example.invalid/t7/kb/002', DATE '2026-07-02',
   'Synthetic caution 002', 'ACTIVE', 'T7-AUTHOR-002', 'T7-APPROVER-002',
   pg_catalog.clock_timestamp()),
  ('70000000-0000-4000-8000-000000000010', 'T7-KB-010', 'OFFICIAL',
   'BULKY_WASTE', 'Synthetic service 010', 'Synthetic summary 010',
   '["step 010"]', '["document 010"]', '10 days', '1000 won',
   'Synthetic department 010', 'Synthetic official source 010',
   'https://example.invalid/t7/kb/010', DATE '2026-07-10',
   'Synthetic caution 010', 'ACTIVE', 'T7-AUTHOR-010', 'T7-APPROVER-010',
   pg_catalog.clock_timestamp()),
  ('70000000-0000-4000-8000-000000000020', 'T7-KB-OTHER', 'OFFICIAL',
   'CERTIFICATE_ISSUANCE', 'Synthetic other intent', 'Synthetic other summary',
   '[]', '[]', NULL, NULL, 'Synthetic other department',
   'Synthetic other source', 'https://example.invalid/t7/kb/other',
   DATE '2026-07-03', NULL, 'ACTIVE', 'T7-AUTHOR-OTHER',
   'T7-APPROVER-OTHER', pg_catalog.clock_timestamp()),
  ('70000000-0000-4000-8000-000000000030', 'T7-KB-MOCK', 'MOCK',
   'BULKY_WASTE', 'Synthetic mock active', 'Synthetic mock summary',
   '[]', '[]', NULL, NULL, 'Synthetic mock department',
   'Synthetic mock source', 'https://example.invalid/t7/kb/mock',
   DATE '2026-07-04', NULL, 'ACTIVE', 'T7-AUTHOR-MOCK',
   'T7-APPROVER-MOCK', pg_catalog.clock_timestamp()),
  ('70000000-0000-4000-8000-000000000041', 'T7-KB-DRAFT', 'OFFICIAL',
   'BULKY_WASTE', 'Synthetic draft', 'Synthetic draft summary', '[]', '[]',
   NULL, NULL, 'Synthetic draft department', 'Synthetic draft source',
   'https://example.invalid/t7/kb/draft', DATE '2026-07-05', NULL, 'DRAFT',
   'T7-AUTHOR-DRAFT', NULL, NULL),
  ('70000000-0000-4000-8000-000000000042', 'T7-KB-PENDING', 'OFFICIAL',
   'BULKY_WASTE', 'Synthetic pending', 'Synthetic pending summary', '[]', '[]',
   NULL, NULL, 'Synthetic pending department', 'Synthetic pending source',
   'https://example.invalid/t7/kb/pending', DATE '2026-07-06', NULL,
   'PENDING', 'T7-AUTHOR-PENDING', NULL, NULL),
  ('70000000-0000-4000-8000-000000000043', 'T7-KB-RETIRED', 'OFFICIAL',
   'BULKY_WASTE', 'Synthetic retired', 'Synthetic retired summary', '[]', '[]',
   NULL, NULL, 'Synthetic retired department', 'Synthetic retired source',
   'https://example.invalid/t7/kb/retired', DATE '2026-07-07', NULL,
   'RETIRED', 'T7-AUTHOR-RETIRED', 'T7-APPROVER-RETIRED',
   pg_catalog.clock_timestamp()),
  ('70000000-0000-4000-8000-000000000044', 'T7-KB-REJECTED', 'OFFICIAL',
   'BULKY_WASTE', 'Synthetic rejected', 'Synthetic rejected summary', '[]', '[]',
   NULL, NULL, 'Synthetic rejected department', 'Synthetic rejected source',
   'https://example.invalid/t7/kb/rejected', DATE '2026-07-08', NULL,
   'REJECTED', 'T7-AUTHOR-REJECTED', NULL, NULL);

INSERT INTO app_private.kb_question_examples (
  kb_document_id, question_example, normalized_text
) VALUES
  ('70000000-0000-4000-8000-000000000002', 'Only example 002',
   'normalized private 002'),
  ('70000000-0000-4000-8000-000000000010', 'Zulu example 010',
   'normalized private zulu'),
  ('70000000-0000-4000-8000-000000000010', 'Alpha example 010',
   'normalized private alpha'),
  ('70000000-0000-4000-8000-000000000010', 'Middle example 010',
   'normalized private middle'),
  ('70000000-0000-4000-8000-000000000020', 'Other intent example', NULL),
  ('70000000-0000-4000-8000-000000000030', 'Mock active example', NULL);

SET CONSTRAINTS ALL IMMEDIATE;

INSERT INTO app_private.offices (
  id, public_id, data_origin, region, office_name, address, phone,
  opening_hours, map_url, source_title, source_url, last_verified_at
) VALUES
  ('71000000-0000-4000-8000-000000000002', 'T7-OFFICE-002', 'OFFICIAL',
   '아름동', 'Synthetic office 002', 'Synthetic address 002', '000-0002',
   '09:00-18:00', 'https://example.invalid/t7/map/002',
   'Synthetic office source 002', 'https://example.invalid/t7/office/002',
   DATE '2026-07-02'),
  ('71000000-0000-4000-8000-000000000010', 'T7-OFFICE-010', 'OFFICIAL',
   '아름동', 'Synthetic office 010', 'Synthetic address 010', '000-0010',
   NULL, NULL, 'Synthetic office source 010',
   'https://example.invalid/t7/office/010', DATE '2026-07-10'),
  ('71000000-0000-4000-8000-000000000020', 'T7-OFFICE-WRONG-REGION',
   'OFFICIAL', '도담동', 'Synthetic wrong region', 'Synthetic address 020',
   '000-0020', NULL, NULL, 'Synthetic office source 020',
   'https://example.invalid/t7/office/020', DATE '2026-07-03'),
  ('71000000-0000-4000-8000-000000000030', 'T7-OFFICE-WRONG-INTENT',
   'OFFICIAL', '아름동', 'Synthetic wrong intent', 'Synthetic address 030',
   '000-0030', NULL, NULL, 'Synthetic office source 030',
   'https://example.invalid/t7/office/030', DATE '2026-07-04'),
  ('71000000-0000-4000-8000-000000000040', 'T7-OFFICE-MOCK', 'MOCK',
   '아름동', 'Synthetic mock office', 'Synthetic address 040', '000-0040',
   NULL, NULL, 'Synthetic mock office source',
   'https://example.invalid/t7/office/mock', DATE '2026-07-05');

INSERT INTO app_private.office_service_mappings (
  office_id, intent, department_label
) VALUES
  ('71000000-0000-4000-8000-000000000002', 'BULKY_WASTE',
   'Synthetic department label 002'),
  ('71000000-0000-4000-8000-000000000010', 'BULKY_WASTE',
   'Synthetic department label 010'),
  ('71000000-0000-4000-8000-000000000020', 'BULKY_WASTE',
   'Synthetic wrong region label'),
  ('71000000-0000-4000-8000-000000000030', 'CERTIFICATE_ISSUANCE',
   'Synthetic wrong intent label'),
  ('71000000-0000-4000-8000-000000000040', 'BULKY_WASTE',
   'Synthetic mock label');

-- Citizen KB rows are exact, ordered, source-authoritative, and expose only
-- each row's lexical question-example array.
SELECT results_eq(
  $actual$
    SELECT public_id
    FROM app_api.list_active_kb('BULKY_WASTE')
  $actual$,
  $expected$
    VALUES ('T7-KB-002'::text), ('T7-KB-010'::text)
  $expected$,
  'matching intent returns only ACTIVE OFFICIAL KBs in public-id order'
);

SELECT results_eq(
  $actual$
    SELECT public_id, category, service_name, answer_summary,
      procedure_steps, required_documents, processing_time, fee, department,
      source_title, source_url, last_verified_at, caution, question_examples
    FROM app_api.list_active_kb('BULKY_WASTE')
    WHERE public_id = 'T7-KB-010'
  $actual$,
  $expected$
    VALUES (
      'T7-KB-010'::text, 'BULKY_WASTE'::text, 'Synthetic service 010'::text,
      'Synthetic summary 010'::text, '["step 010"]'::jsonb,
      '["document 010"]'::jsonb, '10 days'::text, '1000 won'::text,
      'Synthetic department 010'::text, 'Synthetic official source 010'::text,
      'https://example.invalid/t7/kb/010'::text, DATE '2026-07-10',
      'Synthetic caution 010'::text,
      '["Alpha example 010","Middle example 010","Zulu example 010"]'::jsonb
    )
  $expected$,
  'KB public record uses stored source fields and lexical row-local examples'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_api.list_active_kb('CERTIFICATE_ISSUANCE')
  ),
  1,
  'ACTIVE OFFICIAL rows from another supported intent remain independently readable'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_api.list_active_kb('LOCAL_TAX_GENERAL')
  ),
  0,
  'valid supported filter with no match returns zero KB rows'
);

SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_active_kb(NULL)$sql$,
  'P1010', 'INVALID_READ_FILTER', 'KB read rejects NULL intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_active_kb('')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'KB read rejects blank intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_active_kb(' BULKY_WASTE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'KB read rejects padded intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_active_kb('SENTINEL_UNSUPPORTED_INTENT')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'KB read rejects unsupported intent without echo'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_active_kb('OUT_OF_SCOPE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'KB read rejects OUT_OF_SCOPE'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_active_kb('UNKNOWN')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'KB read rejects UNKNOWN'
);

-- Office rows require exact region+intent mappings and OFFICIAL provenance.
SELECT results_eq(
  $actual$
    SELECT public_id
    FROM app_api.list_offices('아름동', 'BULKY_WASTE')
  $actual$,
  $expected$
    VALUES ('T7-OFFICE-002'::text), ('T7-OFFICE-010'::text)
  $expected$,
  'matching region and intent returns only OFFICIAL offices in public-id order'
);

SELECT results_eq(
  $actual$
    SELECT public_id, region, office_name, address, phone, opening_hours,
      map_url, department_label, source_title, source_url, last_verified_at
    FROM app_api.list_offices('아름동', 'BULKY_WASTE')
    WHERE public_id = 'T7-OFFICE-002'
  $actual$,
  $expected$
    VALUES (
      'T7-OFFICE-002'::text, '아름동'::text, 'Synthetic office 002'::text,
      'Synthetic address 002'::text, '000-0002'::text, '09:00-18:00'::text,
      'https://example.invalid/t7/map/002'::text,
      'Synthetic department label 002'::text,
      'Synthetic office source 002'::text,
      'https://example.invalid/t7/office/002'::text, DATE '2026-07-02'
    )
  $expected$,
  'office public record returns exact stored source and mapping fields'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM app_api.list_offices('조치원읍', 'LOCAL_TAX_GENERAL')
  ),
  0,
  'valid supported filters with no match return zero office rows'
);

SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices(NULL, 'BULKY_WASTE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects NULL region'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('', 'BULKY_WASTE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects blank region'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices(' 아름동', 'BULKY_WASTE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects padded region'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('SENTINEL_UNSUPPORTED_REGION', 'BULKY_WASTE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects unsupported region without echo'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', NULL)$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects NULL intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', '')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects blank intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', 'BULKY_WASTE ')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects padded intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', 'SENTINEL_UNSUPPORTED_INTENT')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects unsupported intent without echo'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', 'OUT_OF_SCOPE')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects OUT_OF_SCOPE'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', 'UNKNOWN')$sql$,
  'P1010', 'INVALID_READ_FILTER', 'office read rejects UNKNOWN'
);

-- A real non-superuser member proves the capability works without inheriting
-- base-table SELECT. Diagnostics capture variable values, never literal calls.
CREATE TEMPORARY TABLE task7_error_diagnostics (
  interface_name text NOT NULL,
  returned_sqlstate text NOT NULL,
  message_text text NOT NULL,
  exception_detail text,
  exception_hint text,
  exception_context text,
  schema_name text,
  table_name text,
  column_name text,
  constraint_name text,
  datatype_name text
) ON COMMIT DROP;

CREATE ROLE sejong_task7_backend_probe
  NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT sejong_backend TO sejong_task7_backend_probe WITH ADMIN FALSE;
GRANT sejong_backend TO sejong_task7_backend_probe WITH INHERIT TRUE;
GRANT sejong_backend TO sejong_task7_backend_probe WITH SET FALSE;
GRANT USAGE ON SCHEMA extensions TO sejong_task7_backend_probe;
GRANT INSERT ON task7_error_diagnostics TO sejong_task7_backend_probe;
DO $grant_probe_to_runner$
BEGIN
  EXECUTE pg_catalog.format(
    'GRANT sejong_task7_backend_probe TO %I WITH SET TRUE', CURRENT_USER
  );
END;
$grant_probe_to_runner$;

SET LOCAL ROLE sejong_task7_backend_probe;
SELECT lives_ok(
  $sql$SELECT * FROM app_api.list_active_kb('BULKY_WASTE')$sql$,
  'backend capability executes the citizen KB read'
);
SELECT lives_ok(
  $sql$SELECT * FROM app_api.list_offices('아름동', 'BULKY_WASTE')$sql$,
  'backend capability executes the citizen office read'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_private.kb_documents$sql$,
  '42501', NULL, 'backend cannot SELECT private KB rows'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_private.offices$sql$,
  '42501', NULL, 'backend cannot SELECT private office rows'
);
DO $capture_nonleak$
DECLARE
  v_kb_filter constant text := 'SENTINEL_KB_FILTER_MUST_NOT_LEAK';
  v_office_filter constant text := 'SENTINEL_OFFICE_FILTER_MUST_NOT_LEAK';
  v_state text;
  v_message text;
  v_detail text;
  v_hint text;
  v_context text;
  v_schema text;
  v_table text;
  v_column text;
  v_constraint text;
  v_datatype text;
BEGIN
  BEGIN
    PERFORM * FROM app_api.list_active_kb(v_kb_filter);
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS
      v_state = RETURNED_SQLSTATE,
      v_message = MESSAGE_TEXT,
      v_detail = PG_EXCEPTION_DETAIL,
      v_hint = PG_EXCEPTION_HINT,
      v_context = PG_EXCEPTION_CONTEXT,
      v_schema = SCHEMA_NAME,
      v_table = TABLE_NAME,
      v_column = COLUMN_NAME,
      v_constraint = CONSTRAINT_NAME,
      v_datatype = PG_DATATYPE_NAME;
    INSERT INTO pg_temp.task7_error_diagnostics VALUES (
      'list_active_kb', v_state, v_message, v_detail, v_hint, v_context,
      v_schema, v_table, v_column, v_constraint, v_datatype
    );
  END;

  BEGIN
    PERFORM * FROM app_api.list_offices(
      v_office_filter, v_office_filter
    );
  EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS
      v_state = RETURNED_SQLSTATE,
      v_message = MESSAGE_TEXT,
      v_detail = PG_EXCEPTION_DETAIL,
      v_hint = PG_EXCEPTION_HINT,
      v_context = PG_EXCEPTION_CONTEXT,
      v_schema = SCHEMA_NAME,
      v_table = TABLE_NAME,
      v_column = COLUMN_NAME,
      v_constraint = CONSTRAINT_NAME,
      v_datatype = PG_DATATYPE_NAME;
    INSERT INTO pg_temp.task7_error_diagnostics VALUES (
      'list_offices', v_state, v_message, v_detail, v_hint, v_context,
      v_schema, v_table, v_column, v_constraint, v_datatype
    );
  END;
END;
$capture_nonleak$;
RESET ROLE;

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = relations.relnamespace
    WHERE namespaces.nspname = 'app_private'
      AND relations.relname IN (
        'kb_documents', 'kb_question_examples', 'offices',
        'office_service_mappings', 'interaction_events', 'failed_questions',
        'kb_candidates', 'audit_logs'
      )
      AND pg_catalog.has_table_privilege(
        'sejong_backend', relations.oid, 'SELECT'
      )
  ),
  0,
  'backend has no SELECT privilege on any base table'
);

SELECT ok(
  (
    SELECT pg_catalog.count(*) = 2
      AND pg_catalog.array_agg(interface_name ORDER BY interface_name) =
        ARRAY['list_active_kb', 'list_offices']::text[]
      AND pg_catalog.bool_and(
        returned_sqlstate = 'P1010'
        AND message_text = 'INVALID_READ_FILTER'
        AND pg_catalog.strpos(pg_catalog.concat_ws(
          E'\n', returned_sqlstate, message_text, exception_detail,
          exception_hint, exception_context, schema_name, table_name,
          column_name, constraint_name, datatype_name
        ), 'SENTINEL_KB_FILTER_MUST_NOT_LEAK') = 0
        AND pg_catalog.strpos(pg_catalog.concat_ws(
          E'\n', returned_sqlstate, message_text, exception_detail,
          exception_hint, exception_context, schema_name, table_name,
          column_name, constraint_name, datatype_name
        ), 'SENTINEL_OFFICE_FILTER_MUST_NOT_LEAK') = 0
      )
    FROM task7_error_diagnostics
  ),
  'both fixed read diagnostics omit both caller filter sentinels'
);

SELECT * FROM finish();

ROLLBACK;
