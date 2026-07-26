BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT plan(6);

CREATE TEMPORARY TABLE expected_privileged_functions (
  signature text PRIMARY KEY,
  schema_name text NOT NULL,
  body_md5 text NOT NULL
) ON COMMIT DROP;

INSERT INTO expected_privileged_functions (signature, schema_name, body_md5)
VALUES
  ('app_api.approve_kb_candidate(uuid,text,text,text)', 'app_api', 'ee2586b5fbfdeded31e26f87b045c184'),
  ('app_api.confirm_failed_question_reason(uuid,text,text,text)', 'app_api', '00754b9e5678126271bfc44a4612b0f0'),
  ('app_api.create_kb_candidate(uuid,text,text,text,text,text,text,jsonb,jsonb,text,text,text,text,text,date,text,text)', 'app_api', 'd923e225aa4951b688b2227b8d670f24'),
  ('app_api.list_active_kb(text)', 'app_api', '206bcc0386635d37119bb06060e1b377'),
  ('app_api.list_offices(text,text)', 'app_api', '01a601dcbfbb764df558c9e6bf943a72'),
  ('app_api.purge_expired_failed_question_text()', 'app_api', '7b483406ea9e9bcfe744980df1726fdc'),
  ('app_api.record_interaction(uuid,text,text,text,text[],integer,text,text,boolean,text)', 'app_api', 'f9b6391d53a1439e761d47485cdf61d1'),
  ('app_api.reject_kb_candidate(uuid,text,text,text)', 'app_api', '3c75938f0da17110df63d11f6f09ff9a'),
  ('app_api.submit_kb_candidate(uuid,text,text)', 'app_api', 'a8fdb337ff60e696d10bf8ff32c36ae3'),
  ('app_private.is_allowed_audit_changed_fields(jsonb)', 'app_private', 'a8730fade840afc6a6aac2a6a30f7375'),
  ('app_private.is_nonempty_text(text)', 'app_private', 'ab6b8173673c31beae6d8af598087c5d'),
  ('app_private.is_text_array(jsonb)', 'app_private', '81bf583f0cf037ade8c1f2f3b5f1c13b'),
  ('app_private.is_unique_text_array(jsonb)', 'app_private', '7a10a3a8f8013300fa724c43e66861b0'),
  ('app_private.lock_kb_question_parents()', 'app_private', '736054e7fdf054e32714afeaf89641f2'),
  ('app_private.purge_expired_failed_question_text_at(timestamp with time zone)', 'app_private', '63c9e2a947903f88de690b829a0be3d0'),
  ('app_private.set_updated_at()', 'app_private', '08821b40a10454f2636141839c843559'),
  ('app_private.validate_active_kb_question()', 'app_private', '6014f41ed693231e30a9369dd0e394a4'),
  ('app_private.validate_failed_question_candidate()', 'app_private', '8ca23e41839c992aee9610aa95f13129'),
  ('app_private.validate_failed_question_event()', 'app_private', 'f9aae69d10ca158c0cb6e9db463c04e9'),
  ('app_private.validate_interaction_event_failure()', 'app_private', '5f4dcaa3be52a7fac7e4f005fa946b45'),
  ('app_private.validate_interaction_event_sources()', 'app_private', '576613ddcdb4f499507e5185550a88e3'),
  ('app_private.validate_kb_candidate_failure()', 'app_private', '53b11c56e549da10b63c2e111b11a3a7');

SELECT is(
  (SELECT pg_catalog.count(*)::integer FROM expected_privileged_functions),
  22,
  'the ADR-0018 privileged-function allowlist contains exactly 22 signatures'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM expected_privileged_functions AS expected
    JOIN pg_catalog.pg_proc AS functions
      ON functions.oid = pg_catalog.to_regprocedure(expected.signature)
  ),
  22,
  'all exact privileged-function signatures exist'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM expected_privileged_functions AS expected
    JOIN pg_catalog.pg_proc AS functions
      ON functions.oid = pg_catalog.to_regprocedure(expected.signature)
    WHERE functions.proconfig =
      ARRAY['search_path=pg_catalog, pg_temp']::text[]
  ),
  22,
  'all exact privileged functions use pg_catalog then pg_temp'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM expected_privileged_functions AS expected
    JOIN pg_catalog.pg_proc AS functions
      ON functions.oid = pg_catalog.to_regprocedure(expected.signature)
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE owners.rolname = 'sejong_schema_owner'
  ),
  22,
  'function owners remain unchanged'
);

SELECT results_eq(
  $actual$
    SELECT
      expected.signature COLLATE "C",
      pg_catalog.md5(functions.prosrc) COLLATE "C"
    FROM expected_privileged_functions AS expected
    JOIN pg_catalog.pg_proc AS functions
      ON functions.oid = pg_catalog.to_regprocedure(expected.signature)
    ORDER BY 1
  $actual$,
  $expected$
    SELECT expected.signature COLLATE "C", expected.body_md5 COLLATE "C"
    FROM expected_privileged_functions AS expected
    ORDER BY 1
  $expected$,
  'function bodies remain byte-stable at the catalog source level'
);

SELECT is(
  (
    SELECT pg_catalog.count(*) = 31
      AND pg_catalog.bool_and(
        acl.privilege_type = 'EXECUTE'
        AND (
          grantees.rolname = 'sejong_schema_owner'
          OR (
            expected.schema_name = 'app_api'
            AND grantees.rolname = 'sejong_backend'
          )
        )
      )
    FROM expected_privileged_functions AS expected
    JOIN pg_catalog.pg_proc AS functions
      ON functions.oid = pg_catalog.to_regprocedure(expected.signature)
    CROSS JOIN LATERAL pg_catalog.aclexplode(functions.proacl) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantees ON grantees.oid = acl.grantee
  ),
  true,
  'function ACLs remain owner-only for private helpers and owner-plus-backend for API capabilities'
);

SELECT * FROM finish();

ROLLBACK;
