BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT no_plan();

-- Capability roles, ownership, effective ACLs, and forced RLS.
SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_roles AS roles
    WHERE roles.rolname IN ('sejong_schema_owner', 'sejong_backend')
      AND NOT roles.rolcanlogin
      AND NOT roles.rolsuper
      AND NOT roles.rolcreatedb
      AND NOT roles.rolcreaterole
      AND NOT roles.rolreplication
      AND NOT roles.rolbypassrls
  ),
  2,
  'capability roles exist with every elevated attribute disabled'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_catalog.pg_auth_members AS memberships
    JOIN pg_catalog.pg_roles AS granted_role
      ON granted_role.oid = memberships.roleid
    JOIN pg_catalog.pg_roles AS member_role
      ON member_role.oid = memberships.member
    WHERE granted_role.rolname = 'sejong_schema_owner'
      AND member_role.rolname = CURRENT_USER
      AND memberships.admin_option
  )
  AND EXISTS (
    SELECT 1
    FROM pg_catalog.pg_auth_members AS memberships
    JOIN pg_catalog.pg_roles AS granted_role
      ON granted_role.oid = memberships.roleid
    JOIN pg_catalog.pg_roles AS member_role
      ON member_role.oid = memberships.member
    WHERE granted_role.rolname = 'sejong_schema_owner'
      AND member_role.rolname = CURRENT_USER
      AND memberships.inherit_option
  )
  AND EXISTS (
    SELECT 1
    FROM pg_catalog.pg_auth_members AS memberships
    JOIN pg_catalog.pg_roles AS granted_role
      ON granted_role.oid = memberships.roleid
    JOIN pg_catalog.pg_roles AS member_role
      ON member_role.oid = memberships.member
    WHERE granted_role.rolname = 'sejong_schema_owner'
      AND member_role.rolname = CURRENT_USER
      AND memberships.set_option
  ),
  'migration user keeps ADMIN, INHERIT, and SET for schema owner'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_catalog.pg_auth_members AS memberships
    JOIN pg_catalog.pg_roles AS granted_role
      ON granted_role.oid = memberships.roleid
    JOIN pg_catalog.pg_roles AS member_role
      ON member_role.oid = memberships.member
    WHERE granted_role.rolname = 'sejong_backend'
      AND member_role.rolname = CURRENT_USER
      AND memberships.admin_option
      AND NOT memberships.inherit_option
      AND NOT memberships.set_option
  )
  AND NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_auth_members AS memberships
    JOIN pg_catalog.pg_roles AS granted_role
      ON granted_role.oid = memberships.roleid
    JOIN pg_catalog.pg_roles AS member_role
      ON member_role.oid = memberships.member
    WHERE granted_role.rolname = 'sejong_backend'
      AND member_role.rolname = CURRENT_USER
      AND (memberships.inherit_option OR memberships.set_option)
  ),
  'migration user administers backend without inherited or SET capability'
);

SELECT ok(
  pg_catalog.has_database_privilege(
    'sejong_schema_owner', pg_catalog.current_database(), 'CREATE'
  ),
  'schema owner has current-database CREATE needed for schema ownership'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_namespace AS namespaces
    CROSS JOIN LATERAL pg_catalog.aclexplode(
      COALESCE(namespaces.nspacl, pg_catalog.acldefault('n', namespaces.nspowner))
    ) AS privileges
    WHERE namespaces.nspname = 'public'
      AND privileges.grantee = 0
      AND privileges.privilege_type = 'CREATE'
  ),
  0,
  'PUBLIC cannot create in public schema'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_namespace AS namespaces
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = namespaces.nspowner
    WHERE namespaces.nspname IN ('app_private', 'app_api')
      AND owners.rolname = 'sejong_schema_owner'
  ),
  2,
  'schema owner owns both application schemas'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_type AS types
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = types.typnamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = types.typowner
    WHERE namespaces.nspname = 'app_private'
      AND types.typtype = 'e'
      AND owners.rolname = 'sejong_schema_owner'
  ),
  7,
  'schema owner owns all seven enums'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = relations.relnamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = relations.relowner
    WHERE namespaces.nspname = 'app_private'
      AND relations.relkind = 'r'
      AND owners.rolname = 'sejong_schema_owner'
  ),
  11,
  'schema owner owns all eleven approved local/private base tables'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE namespaces.nspname = 'app_private'
      AND owners.rolname <> 'sejong_schema_owner'
  ),
  0,
  'schema owner owns every private function'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = relations.relnamespace
    WHERE namespaces.nspname = 'app_private'
      AND relations.relkind = 'r'
      AND relations.relrowsecurity
  ),
  11,
  'all eleven approved local/private base tables have RLS enabled'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = relations.relnamespace
    WHERE namespaces.nspname = 'app_private'
      AND relations.relkind = 'r'
      AND relations.relforcerowsecurity
  ),
  11,
  'all eleven approved local/private base tables force RLS'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_policy AS policies
    JOIN pg_catalog.pg_class AS relations ON relations.oid = policies.polrelid
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = relations.relnamespace
    WHERE namespaces.nspname = 'app_private'
  ),
  11,
  'app_private has exactly eleven owner-only policies total'
);

SELECT results_eq(
  $actual$
    SELECT relations.relname::text COLLATE "C",
      policies.polname::text COLLATE "C",
      policies.polcmd::text COLLATE "C",
      policies.polpermissive,
      policies.polroles = ARRAY[
        (SELECT roles.oid FROM pg_catalog.pg_roles AS roles
         WHERE roles.rolname = 'sejong_schema_owner')
      ]::oid[] AS owner_only,
      pg_catalog.pg_get_expr(
        policies.polqual, policies.polrelid
      )::text COLLATE "C" AS using_expression,
      pg_catalog.pg_get_expr(
        policies.polwithcheck, policies.polrelid
      )::text COLLATE "C" AS check_expression
    FROM pg_catalog.pg_policy AS policies
    JOIN pg_catalog.pg_class AS relations ON relations.oid = policies.polrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = relations.relnamespace
    WHERE namespaces.nspname = 'app_private'
    ORDER BY relations.relname COLLATE "C"
  $actual$,
  $expected$
    SELECT expected.table_name COLLATE "C",
      expected.policy_name COLLATE "C",
      expected.command_name COLLATE "C",
      expected.is_permissive,
      expected.owner_only,
      expected.using_expression COLLATE "C",
      expected.check_expression COLLATE "C"
    FROM (
      VALUES
        ('audit_logs'::text, 'audit_logs_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('chat_idempotency'::text, 'chat_idempotency_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('citizen_feedback'::text, 'citizen_feedback_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('civic_scope_gaps'::text, 'civic_scope_gaps_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('failed_questions'::text, 'failed_questions_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('interaction_events'::text, 'interaction_events_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('kb_candidates'::text, 'kb_candidates_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('kb_documents'::text, 'kb_documents_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('kb_question_examples'::text, 'kb_question_examples_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('office_service_mappings'::text,
         'office_service_mappings_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text),
        ('offices'::text, 'offices_owner_all'::text,
         '*'::text, true, true, 'true'::text, 'true'::text)
    ) AS expected(
      table_name, policy_name, command_name, is_permissive, owner_only,
      using_expression, check_expression
    )
    ORDER BY expected.table_name COLLATE "C"
  $expected$,
  'each table has its exact true owner-only permissive FOR ALL policy'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = relations.relnamespace
    CROSS JOIN LATERAL pg_catalog.aclexplode(
      COALESCE(relations.relacl, pg_catalog.acldefault('r', relations.relowner))
    ) AS privileges
    WHERE namespaces.nspname = 'app_private'
      AND relations.relkind = 'r'
      AND privileges.grantee = 0
      AND privileges.privilege_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
  ),
  0,
  'effective ACLs grant no base-table CRUD to PUBLIC'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = relations.relnamespace
    CROSS JOIN pg_catalog.unnest(
      ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    ) AS requested(privilege_name)
    CROSS JOIN pg_catalog.unnest(
      ARRAY['anon', 'authenticated', 'sejong_backend']
    ) AS grantees(role_name)
    WHERE namespaces.nspname = 'app_private'
      AND relations.relkind = 'r'
      AND pg_catalog.has_table_privilege(
        grantees.role_name, relations.oid, requested.privilege_name
      )
  ),
  0,
  'anon, authenticated, and backend have no effective base-table CRUD'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_namespace AS namespaces
    CROSS JOIN LATERAL pg_catalog.aclexplode(
      COALESCE(namespaces.nspacl, pg_catalog.acldefault('n', namespaces.nspowner))
    ) AS privileges
    WHERE namespaces.nspname IN ('app_private', 'app_api')
      AND privileges.grantee = 0
      AND privileges.privilege_type IN ('USAGE', 'CREATE')
  ),
  0,
  'effective schema ACLs grant no application-schema access to PUBLIC'
);

SELECT ok(
  NOT pg_catalog.has_schema_privilege('anon', 'app_private', 'USAGE')
  AND NOT pg_catalog.has_schema_privilege('anon', 'app_api', 'USAGE')
  AND NOT pg_catalog.has_schema_privilege('authenticated', 'app_private', 'USAGE')
  AND NOT pg_catalog.has_schema_privilege('authenticated', 'app_api', 'USAGE')
  AND pg_catalog.has_schema_privilege('sejong_backend', 'app_api', 'USAGE')
  AND NOT pg_catalog.has_schema_privilege('sejong_backend', 'app_private', 'USAGE'),
  'only backend has app_api usage and nobody gains app_private usage'
);

-- Function signatures, SECURITY DEFINER posture, and effective function ACLs.
SELECT ok(
  pg_catalog.to_regprocedure(
    'app_api.record_interaction(uuid,text,text,text,text[],integer,text,text,boolean,text)'
  ) IS NOT NULL,
  'record_interaction exists with approved signature'
);
SELECT ok(
  pg_catalog.to_regprocedure(
    'app_private.purge_expired_failed_question_text_at(timestamptz)'
  ) IS NOT NULL,
  'private cutoff purge helper exists'
);
SELECT ok(
  pg_catalog.to_regprocedure('app_api.purge_expired_failed_question_text()') IS NOT NULL,
  'public no-argument purge wrapper exists'
);
SELECT ok(
  pg_catalog.to_regprocedure(
    'app_api.purge_expired_failed_question_text(timestamptz)'
  ) IS NULL,
  'app_api exposes no caller-controlled cutoff overload'
);

SELECT results_eq(
  $actual$
    SELECT functions.oid
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
    ORDER BY functions.oid
  $actual$,
  $expected$
    SELECT approved.oid
    FROM pg_catalog.unnest(
      pg_catalog.array_remove(
        ARRAY[
          pg_catalog.to_regprocedure('app_api.list_active_kb(text)')::oid,
          pg_catalog.to_regprocedure('app_api.list_offices(text,text)')::oid,
          pg_catalog.to_regprocedure(
            'app_api.record_interaction(uuid,text,text,text,text[],integer,text,text,boolean,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.confirm_failed_question_reason(uuid,text,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.create_kb_candidate(uuid,text,text,text,text,text,text,jsonb,jsonb,text,text,text,text,text,date,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.submit_kb_candidate(uuid,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.approve_kb_candidate(uuid,text,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.approve_kb_candidate_with_public_id(uuid,text,text,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.reject_kb_candidate(uuid,text,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.purge_expired_failed_question_text()'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.list_failed_questions(text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.get_failed_question(uuid)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.list_kb_candidates()'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.get_kb_candidate(uuid)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.claim_chat_idempotency(uuid,text,uuid)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.complete_chat_idempotency(uuid,text,uuid,jsonb)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.abandon_chat_idempotency(uuid,text,uuid)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.purge_expired_chat_idempotency()'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.record_civic_scope_gap(text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.list_civic_scope_gaps(text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.review_civic_scope_gap(uuid,text,text,text,text)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.purge_expired_civic_scope_gap_text()'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.record_citizen_feedback(uuid,text,text,text,text,boolean)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.list_citizen_feedback(integer)'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.summarize_citizen_feedback()'
          )::oid,
          pg_catalog.to_regprocedure(
            'app_api.purge_expired_citizen_feedback_detail()'
          )::oid
        ]::oid[],
        NULL::oid
      )
    ) AS approved(oid)
    ORDER BY approved.oid
  $expected$,
  'app_api contains only approved DB-001 and local MVP interface identities'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
      AND pg_catalog.has_function_privilege(
        'sejong_backend', functions.oid, 'EXECUTE'
      )
      AND functions.oid <> ALL (
        pg_catalog.array_remove(
          ARRAY[
            pg_catalog.to_regprocedure('app_api.list_active_kb(text)')::oid,
            pg_catalog.to_regprocedure('app_api.list_offices(text,text)')::oid,
            pg_catalog.to_regprocedure(
              'app_api.record_interaction(uuid,text,text,text,text[],integer,text,text,boolean,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.confirm_failed_question_reason(uuid,text,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.create_kb_candidate(uuid,text,text,text,text,text,text,jsonb,jsonb,text,text,text,text,text,date,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.submit_kb_candidate(uuid,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.approve_kb_candidate(uuid,text,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.approve_kb_candidate_with_public_id(uuid,text,text,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.reject_kb_candidate(uuid,text,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.purge_expired_failed_question_text()'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.list_failed_questions(text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.get_failed_question(uuid)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.list_kb_candidates()'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.get_kb_candidate(uuid)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.claim_chat_idempotency(uuid,text,uuid)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.complete_chat_idempotency(uuid,text,uuid,jsonb)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.abandon_chat_idempotency(uuid,text,uuid)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.purge_expired_chat_idempotency()'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.record_civic_scope_gap(text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.list_civic_scope_gaps(text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.review_civic_scope_gap(uuid,text,text,text,text)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.purge_expired_civic_scope_gap_text()'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.record_citizen_feedback(uuid,text,text,text,text,boolean)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.list_citizen_feedback(integer)'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.summarize_citizen_feedback()'
            )::oid,
            pg_catalog.to_regprocedure(
              'app_api.purge_expired_citizen_feedback_detail()'
            )::oid
          ]::oid[],
          NULL::oid
        )
      )
  ),
  0,
  'backend has no EXECUTE outside the approved app_api allowlist'
);

SELECT throws_ok(
  $sql$SELECT *
        FROM app_private.purge_expired_failed_question_text_at(NULL)$sql$,
  'P1010', 'INVALID_RETENTION_CUTOFF',
  'private cutoff helper rejects NULL without leaking data'
);

SELECT ok(
  (SELECT pg_catalog.count(*) >= 2
   FROM pg_catalog.pg_proc AS functions
   JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
   WHERE namespaces.nspname = 'app_api')
  AND NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE namespaces.nspname = 'app_api'
      AND (
        owners.rolname <> 'sejong_schema_owner'
        OR NOT functions.prosecdef
        OR functions.proconfig IS DISTINCT FROM
          ARRAY['search_path=pg_catalog, pg_temp']::text[]
      )
  ),
  'every app_api function is schema-owner SECURITY DEFINER with fixed search_path'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    CROSS JOIN LATERAL pg_catalog.aclexplode(
      COALESCE(functions.proacl, pg_catalog.acldefault('f', functions.proowner))
    ) AS privileges
    WHERE namespaces.nspname = 'app_api'
      AND privileges.grantee = 0
      AND privileges.privilege_type = 'EXECUTE'
  ),
  0,
  'effective app_api ACLs grant no PUBLIC execute'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_api'
      AND (
        pg_catalog.has_function_privilege('anon', functions.oid, 'EXECUTE')
        OR pg_catalog.has_function_privilege('authenticated', functions.oid, 'EXECUTE')
        OR NOT pg_catalog.has_function_privilege(
          'sejong_backend', functions.oid, 'EXECUTE'
        )
      )
  ),
  'only backend can execute every reviewed app_api function'
);

SELECT ok(
  (
    SELECT owners.rolname = 'sejong_schema_owner'
      AND functions.proconfig =
        ARRAY['search_path=pg_catalog, pg_temp']::text[]
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE functions.oid = pg_catalog.to_regprocedure(
      'app_private.purge_expired_failed_question_text_at(timestamptz)'
    )
  )
  AND NOT pg_catalog.has_function_privilege(
    'sejong_backend',
    'app_private.purge_expired_failed_question_text_at(timestamptz)',
    'EXECUTE'
  ),
  'private cutoff helper is owner-controlled and unavailable to backend'
);

-- Transaction-scoped synthetic fixtures.
INSERT INTO app_private.kb_documents (
  id, public_id, data_origin, category, service_name, answer_summary,
  procedure_steps, required_documents, department, source_title, source_url,
  last_verified_at, status, created_by, approved_by, approved_at
) VALUES
  (
    '50000000-0000-4000-8000-000000000101', 'T5-KB-ACTIVE-A', 'OFFICIAL',
    'BULKY_WASTE', 'Synthetic active A', 'Synthetic summary A', '[]', '[]',
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t5/active-a', DATE '2026-07-16', 'ACTIVE',
    'T5-OPERATOR', 'T5-APPROVER', TIMESTAMPTZ '2026-07-16 00:00:00+00'
  ),
  (
    '50000000-0000-4000-8000-000000000102', 'T5-KB-ACTIVE-B', 'OFFICIAL',
    'BULKY_WASTE', 'Synthetic active B', 'Synthetic summary B', '[]', '[]',
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t5/active-b', DATE '2026-07-16', 'ACTIVE',
    'T5-OPERATOR', 'T5-APPROVER', TIMESTAMPTZ '2026-07-16 00:00:00+00'
  ),
  (
    '50000000-0000-4000-8000-000000000103', 'T5-KB-DRAFT-OFFICIAL', 'OFFICIAL',
    'BULKY_WASTE', 'Synthetic draft', 'Synthetic draft summary', '[]', '[]',
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t5/draft', DATE '2026-07-16', 'DRAFT',
    'T5-OPERATOR', NULL, NULL
  ),
  (
    '50000000-0000-4000-8000-000000000104', 'T5-KB-DRAFT-MOCK', 'MOCK',
    'BULKY_WASTE', 'Synthetic mock', 'Synthetic mock summary', '[]', '[]',
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t5/mock', DATE '2026-07-16', 'DRAFT',
    'T5-OPERATOR', NULL, NULL
  );

INSERT INTO app_private.kb_question_examples (kb_document_id, question_example)
VALUES
  ('50000000-0000-4000-8000-000000000101', 'Synthetic active question A'),
  ('50000000-0000-4000-8000-000000000102', 'Synthetic active question B');

INSERT INTO app_private.offices (
  id, public_id, data_origin, region, office_name, address, phone,
  source_title, source_url, last_verified_at
) VALUES
  (
    '50000000-0000-4000-8000-000000000111', 'T5-OFFICE-OFFICIAL',
    'OFFICIAL', '아름동', 'Synthetic official office', 'Synthetic address',
    '000-000-0000', 'Synthetic source',
    'https://example.invalid/t5/office-official', DATE '2026-07-16'
  ),
  (
    '50000000-0000-4000-8000-000000000112', 'T5-OFFICE-MOCK',
    'MOCK', '아름동', 'Synthetic mock office', 'Synthetic address',
    '000-000-0000', 'Synthetic source',
    'https://example.invalid/t5/office-mock', DATE '2026-07-16'
  );

CREATE TEMPORARY TABLE task5_results (
  label text PRIMARY KEY,
  interaction_id uuid NOT NULL,
  failed_question_id uuid
) ON COMMIT DROP;

CREATE TEMPORARY TABLE task5_purge_results (
  label text PRIMARY KEY,
  purged_count integer NOT NULL,
  purged_ids uuid[] NOT NULL
) ON COMMIT DROP;

CREATE TEMPORARY TABLE task5_error_diagnostics (
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

-- Exercise RLS through a real non-superuser backend member. Test-only direct
-- grants prove FORCE RLS independently of the production ACL denial.
CREATE ROLE sejong_task5_backend_probe
  NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT sejong_backend TO sejong_task5_backend_probe WITH ADMIN FALSE;
GRANT sejong_backend TO sejong_task5_backend_probe WITH INHERIT TRUE;
GRANT sejong_backend TO sejong_task5_backend_probe WITH SET FALSE;
DO $grant_probe_to_runner$
BEGIN
  EXECUTE pg_catalog.format(
    'GRANT sejong_task5_backend_probe TO %I WITH SET TRUE',
    CURRENT_USER
  );
END;
$grant_probe_to_runner$;
GRANT USAGE ON SCHEMA app_private TO sejong_task5_backend_probe;
GRANT USAGE ON SCHEMA extensions TO sejong_task5_backend_probe;
GRANT SELECT, INSERT ON app_private.interaction_events
  TO sejong_task5_backend_probe;
GRANT INSERT ON task5_error_diagnostics TO sejong_task5_backend_probe;

SET LOCAL ROLE sejong_task5_backend_probe;
SELECT is(
  (SELECT pg_catalog.count(*)::integer FROM app_private.interaction_events),
  0,
  'non-superuser backend probe sees no rows through forced RLS'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids,
    response_time_ms, is_test, request_id
  ) VALUES (
    'UNKNOWN', 'SYSTEM_ERROR', 0, '[]', 1, true,
    '50000000-0000-4000-8000-000000000201'
  )$sql$,
  '42501', NULL, 'non-superuser backend probe cannot insert through forced RLS'
);
SELECT lives_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000202',
    'UNKNOWN', 'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1,
    NULL, NULL, true, NULL
  )$sql$,
  'backend probe can execute reviewed SECURITY DEFINER interface'
);
RESET ROLE;
SELECT is(
  (SELECT pg_catalog.count(*)::integer
   FROM app_private.interaction_events
   WHERE request_id = '50000000-0000-4000-8000-000000000202'),
  1,
  'backend RPC writes exactly one metadata event'
);

-- Every typed caller input is checked before native table casts/constraints.
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    NULL, 'UNKNOWN', 'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1,
    NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL request ID maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000211', NULL,
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL intent maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000212', 'INVALID_INTENT',
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'invalid intent maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000213', 'UNKNOWN',
    NULL, NULL, ARRAY[]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL answer status maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000214', 'UNKNOWN',
    'INVALID_STATUS', NULL, ARRAY[]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'invalid answer status maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000215', 'BULKY_WASTE',
    'FALLBACK', 'INVALID_REASON', ARRAY[]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'invalid fallback reason maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000216', 'UNKNOWN',
    'SYSTEM_ERROR', NULL, NULL::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL source array maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000217', 'BULKY_WASTE',
    'SUCCESS', NULL, ARRAY[NULL]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL source ID maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000218', 'BULKY_WASTE',
    'SUCCESS', NULL, ARRAY[' '], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'blank source ID maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000219', 'BULKY_WASTE',
    'SUCCESS', NULL, ARRAY['T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-A'],
    1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'duplicate source IDs map to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000220', 'UNKNOWN',
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], NULL, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL response time maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000221', 'UNKNOWN',
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], -1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'negative response time maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000222', 'UNKNOWN',
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1, '세종시', NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'unsupported region maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000223', 'UNKNOWN',
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1, NULL, ' ', true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'blank office ID maps to stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000224', 'UNKNOWN',
    'SYSTEM_ERROR', NULL, ARRAY[]::text[], 1, NULL, NULL, NULL, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'NULL is_test maps to stable P1010'
);
SET LOCAL ROLE sejong_task5_backend_probe;
DO $capture_nonleak$
DECLARE
  v_sentinel constant text := 'MASKED_SENTINEL_MUST_NOT_LEAK ';
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
    PERFORM 1
    FROM app_api.record_interaction(
      '50000000-0000-4000-8000-000000000225', 'BULKY_WASTE',
      'FALLBACK', 'PERSONAL_LOOKUP', ARRAY[]::text[], 1,
      NULL, NULL, true, v_sentinel
    );

    INSERT INTO pg_temp.task5_error_diagnostics
    VALUES (
      '00000', 'NO_ERROR', NULL, NULL, NULL,
      NULL, NULL, NULL, NULL, NULL
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

    INSERT INTO pg_temp.task5_error_diagnostics
    VALUES (
      v_state, v_message, v_detail, v_hint, v_context,
      v_schema, v_table, v_column, v_constraint, v_datatype
    );
  END;
END;
$capture_nonleak$;
RESET ROLE;

SELECT ok(
  (
    SELECT pg_catalog.count(*) = 1
      AND pg_catalog.bool_and(
        diagnostics.returned_sqlstate = 'P1010'
        AND diagnostics.message_text = 'INVALID_INTERACTION'
        AND pg_catalog.strpos(
          pg_catalog.concat_ws(
            E'\n', diagnostics.returned_sqlstate,
            diagnostics.message_text, diagnostics.exception_detail,
            diagnostics.exception_hint, diagnostics.exception_context,
            diagnostics.schema_name, diagnostics.table_name,
            diagnostics.column_name, diagnostics.constraint_name,
            diagnostics.datatype_name
          ),
          'MASKED_SENTINEL_MUST_NOT_LEAK'
        ) = 0
      )
    FROM task5_error_diagnostics AS diagnostics
  )
  AND NOT EXISTS (
    SELECT 1
    FROM app_private.interaction_events AS events
    WHERE events.request_id = '50000000-0000-4000-8000-000000000225'
  ),
  'real backend member gets stable nonleaking diagnostics and zero writes'
);

-- SUCCESS provenance, exact metadata, sequential replay, and conflict.
INSERT INTO task5_results
SELECT 'success-first', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000301', 'BULKY_WASTE', 'SUCCESS', NULL,
  ARRAY['T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B'], 17,
  '아름동', 'T5-OFFICE-OFFICIAL', true, NULL
) AS result;
INSERT INTO task5_results
SELECT 'success-replay', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000301', 'BULKY_WASTE', 'SUCCESS', NULL,
  ARRAY['T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B'], 17,
  '아름동', 'T5-OFFICE-OFFICIAL', true, NULL
) AS result;

SELECT ok(
  (SELECT first.interaction_id = replay.interaction_id
     AND first.failed_question_id IS NULL
     AND replay.failed_question_id IS NULL
   FROM task5_results AS first
   JOIN task5_results AS replay ON replay.label = 'success-replay'
   WHERE first.label = 'success-first')
  AND (SELECT pg_catalog.count(*) = 1
       FROM app_private.interaction_events
       WHERE request_id = '50000000-0000-4000-8000-000000000301'),
  'identical replay returns existing IDs and writes no duplicate'
);

UPDATE app_private.kb_documents
SET status = 'DRAFT', data_origin = 'MOCK'
WHERE public_id IN ('T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B');
UPDATE app_private.offices
SET data_origin = 'MOCK'
WHERE public_id = 'T5-OFFICE-OFFICIAL';

SELECT lives_ok(
  $sql$
    INSERT INTO task5_results
    SELECT 'success-replay-after-provenance-change',
      result.interaction_id, result.failed_question_id
    FROM app_api.record_interaction(
      '50000000-0000-4000-8000-000000000301',
      'BULKY_WASTE', 'SUCCESS', NULL,
      ARRAY['T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B'], 17,
      '아름동', 'T5-OFFICE-OFFICIAL', true, NULL
    ) AS result
  $sql$,
  'identical replay does not revalidate mutable source or office provenance'
);

SELECT ok(
  (SELECT first.interaction_id = replay.interaction_id
     AND first.failed_question_id IS NULL
     AND replay.failed_question_id IS NULL
   FROM task5_results AS first
   JOIN task5_results AS replay
     ON replay.label = 'success-replay-after-provenance-change'
   WHERE first.label = 'success-first')
  AND (SELECT pg_catalog.count(*) = 1
       FROM app_private.interaction_events
       WHERE request_id = '50000000-0000-4000-8000-000000000301'),
  'provenance-stable replay returns prior IDs and writes no duplicate'
);

UPDATE app_private.kb_documents
SET status = 'ACTIVE', data_origin = 'OFFICIAL'
WHERE public_id IN ('T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B');
UPDATE app_private.offices
SET data_origin = 'OFFICIAL'
WHERE public_id = 'T5-OFFICE-OFFICIAL';

SELECT ok(
  EXISTS (
    SELECT 1
    FROM app_private.interaction_events AS events
    WHERE events.request_id = '50000000-0000-4000-8000-000000000301'
      AND events.source_count = 2
      AND events.used_source_ids =
        pg_catalog.to_jsonb(ARRAY['T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B'])
      AND events.response_time_ms = 17
      AND events.selected_region = '아름동'
      AND events.routed_office_id =
        '50000000-0000-4000-8000-000000000111'
      AND events.is_test
  ),
  'SUCCESS stores to_jsonb source order, cardinality, and official office ID'
);

SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000301', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY['T5-KB-ACTIVE-A', 'T5-KB-ACTIVE-B'], 18,
    '아름동', 'T5-OFFICE-OFFICIAL', true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'conflicting replay raises stable P1010'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000301', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY['T5-KB-ACTIVE-B', 'T5-KB-ACTIVE-A'], 17,
    '아름동', 'T5-OFFICE-OFFICIAL', true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'source order is replay metadata'
);

SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000302', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY['T5-KB-DRAFT-OFFICIAL'], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'SUCCESS rejects non-ACTIVE source'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000303', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY['T5-KB-DRAFT-MOCK'], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'SUCCESS rejects MOCK source'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000304', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY[]::text[], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'SUCCESS requires source'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000305', 'UNKNOWN', 'SUCCESS', NULL,
    ARRAY['T5-KB-ACTIVE-A'], 1, NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'SUCCESS requires supported intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000306', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY['T5-KB-ACTIVE-A'], 1, NULL, NULL, true, '[MASKED] prohibited'
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'SUCCESS rejects retained text'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000307', 'BULKY_WASTE', 'SUCCESS', NULL,
    ARRAY['T5-KB-ACTIVE-A'], 1, NULL, 'T5-OFFICE-MOCK', true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'routing rejects MOCK office'
);

-- FOLLOWUP and OUT_OF_SCOPE are metadata-only. Supported masked fallbacks
-- create at most one correctly eligible failure; missing text creates none.
INSERT INTO task5_results
SELECT 'followup', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000321',
  'UNKNOWN', 'FOLLOWUP', NULL, ARRAY[]::text[], 21,
  NULL, NULL, true, NULL
) AS result;
SELECT ok(
  (SELECT failed_question_id IS NULL FROM task5_results WHERE label = 'followup')
  AND NOT EXISTS (
    SELECT 1 FROM app_private.failed_questions AS failures
    JOIN app_private.interaction_events AS events
      ON events.id = failures.interaction_event_id
    WHERE events.request_id = '50000000-0000-4000-8000-000000000321'
  ),
  'FOLLOWUP creates event only and no failed row'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000322',
    'UNKNOWN', 'FOLLOWUP', NULL, ARRAY[]::text[], 1,
    NULL, NULL, true, '[MASKED] prohibited'
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'FOLLOWUP rejects retained text'
);

INSERT INTO task5_results
SELECT 'out-of-scope', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000323',
  'OUT_OF_SCOPE', 'FALLBACK', 'OUT_OF_SCOPE', ARRAY[]::text[], 23,
  NULL, NULL, true, NULL
) AS result;
SELECT ok(
  (SELECT failed_question_id IS NULL
   FROM task5_results WHERE label = 'out-of-scope')
  AND NOT EXISTS (
    SELECT 1 FROM app_private.failed_questions AS failures
    JOIN app_private.interaction_events AS events
      ON events.id = failures.interaction_event_id
    WHERE events.request_id = '50000000-0000-4000-8000-000000000323'
  ),
  'OUT_OF_SCOPE creates event only and no failed row'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000324',
    'OUT_OF_SCOPE', 'FALLBACK', 'OUT_OF_SCOPE', ARRAY[]::text[], 1,
    NULL, NULL, true, '[MASKED] prohibited'
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'OUT_OF_SCOPE rejects retained text'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000325',
    'BULKY_WASTE', 'FALLBACK', 'OUT_OF_SCOPE', ARRAY[]::text[], 1,
    NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'OUT_OF_SCOPE reason requires matching intent'
);

INSERT INTO task5_results
SELECT 'insufficient', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000326',
  'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING', ARRAY[]::text[], 26,
  NULL, NULL, true, '[MASKED] synthetic insufficient'
) AS result;
INSERT INTO task5_results
SELECT 'personal', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000327',
  'LOCAL_TAX_GENERAL', 'FALLBACK', 'PERSONAL_LOOKUP', ARRAY[]::text[], 27,
  NULL, NULL, true, '[MASKED] synthetic personal'
) AS result;
INSERT INTO task5_results
SELECT 'legal', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000328',
  'MOVE_IN_RESIDENT_REGISTRATION', 'FALLBACK', 'LEGAL_JUDGMENT',
  ARRAY[]::text[], 28, NULL, NULL, true, '[MASKED] synthetic legal'
) AS result;

SELECT ok(
  (SELECT failures.candidate_eligible
   FROM task5_results AS results
   JOIN app_private.failed_questions AS failures
     ON failures.id = results.failed_question_id
   WHERE results.label = 'insufficient')
  AND NOT (SELECT failures.candidate_eligible
           FROM task5_results AS results
           JOIN app_private.failed_questions AS failures
             ON failures.id = results.failed_question_id
           WHERE results.label = 'personal')
  AND NOT (SELECT failures.candidate_eligible
           FROM task5_results AS results
           JOIN app_private.failed_questions AS failures
             ON failures.id = results.failed_question_id
           WHERE results.label = 'legal'),
  'only retained INSUFFICIENT_GROUNDING is candidate eligible'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM task5_results AS results
    JOIN app_private.failed_questions AS failures
      ON failures.id = results.failed_question_id
    WHERE results.label IN ('insufficient', 'personal', 'legal')
      AND (
        failures.masked_question IS NULL
        OR failures.text_expires_at <>
          failures.created_at + interval '30 days'
        OR failures.text_purged_at IS NOT NULL
      )
  ),
  'retained supported failures start with exact 30-day lifecycle'
);

INSERT INTO task5_results
SELECT 'missing-masked', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000329',
  'LOCAL_TAX_GENERAL', 'FALLBACK', 'PERSONAL_LOOKUP', ARRAY[]::text[], 29,
  NULL, NULL, true, NULL
) AS result;
SELECT ok(
  (SELECT failed_question_id IS NULL
   FROM task5_results WHERE label = 'missing-masked')
  AND (SELECT pg_catalog.count(*) = 1
       FROM app_private.interaction_events
       WHERE request_id = '50000000-0000-4000-8000-000000000329'),
  'missing masked value creates event only'
);

INSERT INTO task5_results
SELECT 'system-error', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000330',
  'OUT_OF_SCOPE', 'SYSTEM_ERROR', NULL, ARRAY[]::text[], 30,
  NULL, NULL, true, NULL
) AS result;
SELECT ok(
  (SELECT failed_question_id IS NULL
   FROM task5_results WHERE label = 'system-error')
  AND (SELECT pg_catalog.count(*) = 1
       FROM app_private.interaction_events
       WHERE request_id = '50000000-0000-4000-8000-000000000330'),
  'SYSTEM_ERROR accepts recognized intent and stores metadata only'
);

SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000331',
    'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING',
    ARRAY['T5-KB-ACTIVE-A'], 1, NULL, NULL, true, '[MASKED] synthetic'
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'supported fallback rejects sources'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000332',
    'UNKNOWN', 'FALLBACK', 'INSUFFICIENT_GROUNDING',
    ARRAY[]::text[], 1, NULL, NULL, true, '[MASKED] synthetic'
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'supported fallback rejects UNKNOWN intent'
);
SELECT throws_ok(
  $sql$SELECT * FROM app_api.record_interaction(
    '50000000-0000-4000-8000-000000000333',
    'UNKNOWN', 'SYSTEM_ERROR', 'PERSONAL_LOOKUP', ARRAY[]::text[], 1,
    NULL, NULL, true, NULL
  )$sql$,
  'P1010', 'INVALID_INTERACTION', 'SYSTEM_ERROR rejects fallback reason'
);

-- Private cutoff: just-before and equal purge; just-after survives.
INSERT INTO task5_results
SELECT 'purge-before', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000341',
  'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING', ARRAY[]::text[], 41,
  NULL, NULL, true, '[MASKED] purge before boundary'
) AS result;
INSERT INTO task5_results
SELECT 'purge-equal', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000342',
  'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING', ARRAY[]::text[], 42,
  NULL, NULL, true, '[MASKED] purge equal boundary'
) AS result;
INSERT INTO task5_results
SELECT 'purge-after', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000343',
  'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING', ARRAY[]::text[], 43,
  NULL, NULL, true, '[MASKED] preserve after boundary'
) AS result;

UPDATE app_private.failed_questions AS failures
SET created_at = boundary.expires_at - interval '30 days',
    text_expires_at = boundary.expires_at
FROM (
  SELECT results.failed_question_id,
    CASE results.label
      WHEN 'purge-before' THEN TIMESTAMPTZ '2026-07-16 11:59:59.999999+00'
      WHEN 'purge-equal' THEN TIMESTAMPTZ '2026-07-16 12:00:00+00'
      ELSE TIMESTAMPTZ '2026-07-16 12:00:00.000001+00'
    END AS expires_at
  FROM task5_results AS results
  WHERE results.label IN ('purge-before', 'purge-equal', 'purge-after')
) AS boundary
WHERE failures.id = boundary.failed_question_id;

-- A real candidate link proves purge never deletes the failure lineage.
UPDATE app_private.failed_questions AS failures
SET status = 'REASON_CONFIRMED'
FROM task5_results AS results
WHERE results.label = 'purge-equal'
  AND failures.id = results.failed_question_id;

INSERT INTO app_private.kb_candidates (
  failed_question_id, title, representative_question, data_origin, category,
  answer_summary, procedure_steps, required_documents, department,
  source_title, source_url, last_verified_at, created_by
)
SELECT results.failed_question_id,
  'Synthetic retained-link candidate', 'Synthetic generalized question',
  'MOCK', 'BULKY_WASTE', 'Synthetic candidate summary', '[]', '[]',
  'Synthetic department', 'Synthetic source',
  'https://example.invalid/t5/candidate-link', DATE '2026-07-16', 'T5-OPERATOR'
FROM task5_results AS results
WHERE results.label = 'purge-equal';

INSERT INTO task5_purge_results
SELECT 'private-first', result.purged_count, result.purged_ids
FROM app_private.purge_expired_failed_question_text_at(
  TIMESTAMPTZ '2026-07-16 12:00:00+00'
) AS result;

SELECT ok(
  (SELECT purged_count = 2
   FROM task5_purge_results WHERE label = 'private-first')
  AND (
    SELECT purged_ids = (
      SELECT pg_catalog.array_agg(results.failed_question_id
                                  ORDER BY results.failed_question_id)
      FROM task5_results AS results
      WHERE results.label IN ('purge-before', 'purge-equal')
    )
    FROM task5_purge_results
    WHERE label = 'private-first'
  ),
  'private purge includes before/equal boundary and returns sorted IDs'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM task5_results AS results
    JOIN app_private.failed_questions AS failures
      ON failures.id = results.failed_question_id
    WHERE results.label IN ('purge-before', 'purge-equal')
      AND (
        failures.masked_question IS NOT NULL
        OR failures.text_purged_at IS DISTINCT FROM
          TIMESTAMPTZ '2026-07-16 12:00:00+00'
      )
  )
  AND EXISTS (
    SELECT 1
    FROM task5_results AS results
    JOIN app_private.failed_questions AS failures
      ON failures.id = results.failed_question_id
    WHERE results.label = 'purge-after'
      AND failures.masked_question IS NOT NULL
      AND failures.text_purged_at IS NULL
  ),
  'private purge leaves just-after text unchanged'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM app_private.kb_candidates AS candidates
    JOIN task5_results AS results
      ON results.failed_question_id = candidates.failed_question_id
    JOIN app_private.failed_questions AS failures
      ON failures.id = candidates.failed_question_id
    JOIN app_private.interaction_events AS events
      ON events.id = failures.interaction_event_id
    WHERE results.label = 'purge-equal'
      AND events.id = results.interaction_id
      AND failures.masked_question IS NULL
  ),
  'purge preserves event, failure, and candidate links'
);

INSERT INTO task5_purge_results
SELECT 'private-second', result.purged_count, result.purged_ids
FROM app_private.purge_expired_failed_question_text_at(
  TIMESTAMPTZ '2026-07-16 12:00:00+00'
) AS result;
SELECT ok(
  (SELECT purged_count = 0 AND purged_ids = ARRAY[]::uuid[]
   FROM task5_purge_results WHERE label = 'private-second'),
  'private purge is idempotent with empty UUID array'
);

-- Public wrapper captures DB time, has no cutoff input, and remains idempotent.
WITH expiry AS (
  SELECT pg_catalog.clock_timestamp() - interval '1 second' AS expires_at
)
UPDATE app_private.failed_questions AS failures
SET created_at = expiry.expires_at - interval '30 days',
    text_expires_at = expiry.expires_at
FROM expiry, task5_results AS results
WHERE results.label = 'purge-after'
  AND failures.id = results.failed_question_id;

INSERT INTO task5_purge_results
SELECT 'public-first', result.purged_count, result.purged_ids
FROM app_api.purge_expired_failed_question_text() AS result;
INSERT INTO task5_purge_results
SELECT 'public-second', result.purged_count, result.purged_ids
FROM app_api.purge_expired_failed_question_text() AS result;

SELECT ok(
  (SELECT purged_count = 1
     AND purged_ids = ARRAY[(
       SELECT failed_question_id FROM task5_results WHERE label = 'purge-after'
     )]::uuid[]
   FROM task5_purge_results WHERE label = 'public-first')
  AND (SELECT purged_count = 0 AND purged_ids = ARRAY[]::uuid[]
       FROM task5_purge_results WHERE label = 'public-second')
  AND EXISTS (
    SELECT 1
    FROM task5_results AS results
    JOIN app_private.failed_questions AS failures
      ON failures.id = results.failed_question_id
    WHERE results.label = 'purge-after'
      AND failures.masked_question IS NULL
      AND failures.text_purged_at >= failures.text_expires_at
  ),
  'public purge uses DB time, NULLs only expired text, and is idempotent'
);

-- Replay metadata excludes masked text and cannot restore purged text.
INSERT INTO task5_results
SELECT 'purge-equal-replay', result.interaction_id, result.failed_question_id
FROM app_api.record_interaction(
  '50000000-0000-4000-8000-000000000342',
  'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING', ARRAY[]::text[], 42,
  NULL, NULL, true, '[MASKED] replay must never restore purged text'
) AS result;
SELECT ok(
  (SELECT original.interaction_id = replay.interaction_id
     AND original.failed_question_id = replay.failed_question_id
   FROM task5_results AS original
   JOIN task5_results AS replay ON replay.label = 'purge-equal-replay'
   WHERE original.label = 'purge-equal')
  AND EXISTS (
    SELECT 1
    FROM task5_results AS results
    JOIN app_private.failed_questions AS failures
      ON failures.id = results.failed_question_id
    WHERE results.label = 'purge-equal'
      AND failures.masked_question IS NULL
  ),
  'identical replay neither compares nor restores purged masked text'
);

SELECT * FROM finish();

ROLLBACK;
