BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT no_plan();

-- Every fixture is synthetic and transaction scoped. OFFICIAL exercises only
-- the provenance branch; this file never seeds citizen-facing data.
INSERT INTO app_private.interaction_events (
  id, intent, answer_status, fallback_reason, source_count, used_source_ids,
  response_time_ms, is_test, request_id
) VALUES
  ('60000000-0000-4000-8000-000000000201', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000211'),
  ('60000000-0000-4000-8000-000000000202', 'BULKY_WASTE', 'FALLBACK',
   'PERSONAL_LOOKUP', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000212'),
  ('60000000-0000-4000-8000-000000000203', 'BULKY_WASTE', 'FALLBACK',
   'LEGAL_JUDGMENT', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000213'),
  ('60000000-0000-4000-8000-000000000204', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000214'),
  ('60000000-0000-4000-8000-000000000205', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000215'),
  ('60000000-0000-4000-8000-000000000206', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000216'),
  ('60000000-0000-4000-8000-000000000207', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000217'),
  ('60000000-0000-4000-8000-000000000208', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000218'),
  ('60000000-0000-4000-8000-000000000209', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000219'),
  ('60000000-0000-4000-8000-000000000210', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000220'),
  ('60000000-0000-4000-8000-000000000221', 'BULKY_WASTE', 'FALLBACK',
   'INSUFFICIENT_GROUNDING', 0, '[]', 1, true,
   '60000000-0000-4000-8000-000000000231');

INSERT INTO app_private.failed_questions (
  id, interaction_event_id, masked_question, intent, fallback_reason,
  candidate_eligible, status
) VALUES
  ('60000000-0000-4000-8000-000000000301',
   '60000000-0000-4000-8000-000000000201', '[MASKED] synthetic same reason',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000302',
   '60000000-0000-4000-8000-000000000202', '[MASKED] synthetic corrected eligible',
   'BULKY_WASTE', 'PERSONAL_LOOKUP', false, 'NEW'),
  ('60000000-0000-4000-8000-000000000303',
   '60000000-0000-4000-8000-000000000203', '[MASKED] synthetic reason only',
   'BULKY_WASTE', 'LEGAL_JUDGMENT', false, 'NEW'),
  ('60000000-0000-4000-8000-000000000304',
   '60000000-0000-4000-8000-000000000204', '[MASKED] synthetic remains new',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000305',
   '60000000-0000-4000-8000-000000000205', '[MASKED] synthetic corrected ineligible',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000306',
   '60000000-0000-4000-8000-000000000206', '[MASKED] synthetic official approval',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000307',
   '60000000-0000-4000-8000-000000000207', '[MASKED] synthetic mock approval',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000308',
   '60000000-0000-4000-8000-000000000208', '[MASKED] synthetic rejection',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000309',
   '60000000-0000-4000-8000-000000000209', '[MASKED] synthetic drafted state',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000310',
   '60000000-0000-4000-8000-000000000210', '[MASKED] synthetic rollback',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW'),
  ('60000000-0000-4000-8000-000000000311',
   '60000000-0000-4000-8000-000000000221', '[MASKED] synthetic late rollback',
   'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'NEW');

CREATE TEMPORARY TABLE task6_candidates (
  label text PRIMARY KEY,
  candidate_id uuid NOT NULL
) ON COMMIT DROP;

CREATE TEMPORARY TABLE task6_error_diagnostics (
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

-- Exact interfaces, ownership, SECURITY DEFINER posture, fixed search path,
-- and backend-only execution are catalog-enforced.
SELECT results_eq(
  $actual$
    SELECT functions.oid
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    WHERE functions.oid = ANY (ARRAY[
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
        'app_api.reject_kb_candidate(uuid,text,text,text)'
      )::oid
    ]::oid[])
    ORDER BY functions.oid
  $actual$,
  $expected$
    SELECT approved.oid
    FROM pg_catalog.unnest(ARRAY[
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
        'app_api.reject_kb_candidate(uuid,text,text,text)'
      )::oid
    ]::oid[]) AS approved(oid)
    ORDER BY approved.oid
  $expected$,
  'all five workflow interfaces exist with exact identities'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = functions.pronamespace
    JOIN pg_catalog.pg_roles AS owners ON owners.oid = functions.proowner
    WHERE functions.oid = ANY (ARRAY[
      'app_api.confirm_failed_question_reason(uuid,text,text,text)'::regprocedure::oid,
      'app_api.create_kb_candidate(uuid,text,text,text,text,text,text,jsonb,jsonb,text,text,text,text,text,date,text,text)'::regprocedure::oid,
      'app_api.submit_kb_candidate(uuid,text,text)'::regprocedure::oid,
      'app_api.approve_kb_candidate(uuid,text,text,text)'::regprocedure::oid,
      'app_api.reject_kb_candidate(uuid,text,text,text)'::regprocedure::oid
    ]::oid[])
      AND namespaces.nspname = 'app_api'
      AND owners.rolname = 'sejong_schema_owner'
      AND functions.prosecdef
      AND functions.proconfig =
        ARRAY['search_path=pg_catalog, pg_temp']::text[]
  ),
  5,
  'workflow interfaces are owner SECURITY DEFINER with fixed search_path'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_proc AS functions
    WHERE functions.oid = ANY (ARRAY[
      'app_api.confirm_failed_question_reason(uuid,text,text,text)'::regprocedure::oid,
      'app_api.create_kb_candidate(uuid,text,text,text,text,text,text,jsonb,jsonb,text,text,text,text,text,date,text,text)'::regprocedure::oid,
      'app_api.submit_kb_candidate(uuid,text,text)'::regprocedure::oid,
      'app_api.approve_kb_candidate(uuid,text,text,text)'::regprocedure::oid,
      'app_api.reject_kb_candidate(uuid,text,text,text)'::regprocedure::oid
    ]::oid[])
      AND (
        pg_catalog.has_function_privilege('anon', functions.oid, 'EXECUTE')
        OR pg_catalog.has_function_privilege('authenticated', functions.oid, 'EXECUTE')
        OR NOT pg_catalog.has_function_privilege(
          'sejong_backend', functions.oid, 'EXECUTE'
        )
      )
  ),
  'anon and authenticated cannot execute while backend can'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    CROSS JOIN LATERAL pg_catalog.aclexplode(
      COALESCE(functions.proacl, pg_catalog.acldefault('f', functions.proowner))
    ) AS privileges
    WHERE functions.oid = ANY (ARRAY[
      'app_api.confirm_failed_question_reason(uuid,text,text,text)'::regprocedure::oid,
      'app_api.create_kb_candidate(uuid,text,text,text,text,text,text,jsonb,jsonb,text,text,text,text,text,date,text,text)'::regprocedure::oid,
      'app_api.submit_kb_candidate(uuid,text,text)'::regprocedure::oid,
      'app_api.approve_kb_candidate(uuid,text,text,text)'::regprocedure::oid,
      'app_api.reject_kb_candidate(uuid,text,text,text)'::regprocedure::oid
    ]::oid[])
      AND privileges.grantee = 0
      AND privileges.privilege_type = 'EXECUTE'
  ),
  0,
  'workflow interfaces grant no effective PUBLIC execute'
);

SELECT ok(
  pg_catalog.pg_get_functiondef(
    'app_private.validate_failed_question_event()'::regprocedure
  ) ~ 'FOR[[:space:]]+SHARE'
  AND pg_catalog.pg_get_functiondef(
    'app_private.validate_failed_question_event()'::regprocedure
  ) !~ 'FOR[[:space:]]+UPDATE',
  'failure lineage takes a parent SHARE lock compatible with replay ordering'
);

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_trigger AS triggers
    JOIN pg_catalog.pg_class AS tables ON tables.oid = triggers.tgrelid
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = tables.relnamespace
    JOIN pg_catalog.pg_proc AS functions ON functions.oid = triggers.tgfoid
    WHERE namespaces.nspname = 'app_private'
      AND tables.relname = 'failed_questions'
      AND triggers.tgname = 'trg_failed_questions_validate_event'
      AND NOT triggers.tgisinternal
      AND functions.proname = 'validate_failed_question_event'
      AND (
        SELECT pg_catalog.array_agg(attributes.attname::text ORDER BY attributes.attname)
        FROM pg_catalog.unnest(triggers.tgattr::smallint[]) AS numbers(attnum)
        JOIN pg_catalog.pg_attribute AS attributes
          ON attributes.attrelid = tables.oid
          AND attributes.attnum = numbers.attnum
      ) = ARRAY[
        'fallback_reason', 'intent', 'interaction_event_id', 'status'
      ]::text[]
  ),
  1,
  'status-only changes also fire event-lineage validation'
);

-- Confirmation role, reason, state, lineage, changed-field order, and event
-- immutability. The parent event always retains its automated reason.
SELECT throws_ok(
  $sql$SELECT app_api.confirm_failed_question_reason(
    '60000000-0000-4000-8000-000000000301', 'T6-APPROVER', 'APPROVER',
    'INSUFFICIENT_GROUNDING'
  )$sql$,
  'P1001', 'FORBIDDEN_ACTOR', 'only OPERATOR can confirm a reason'
);
SELECT throws_ok(
  $sql$SELECT app_api.confirm_failed_question_reason(
    '60000000-0000-4000-8000-000000000301', 'T6-OPERATOR', 'OPERATOR',
    'OUT_OF_SCOPE'
  )$sql$,
  'P1010', 'INVALID_FAILURE_REASON', 'confirmation rejects an unstored reason'
);
SELECT is(
  (SELECT pg_catalog.count(*)::integer FROM app_private.audit_logs),
  0,
  'failed confirmations write no audit row'
);

SELECT lives_ok(
  $sql$SELECT app_api.confirm_failed_question_reason(
    '60000000-0000-4000-8000-000000000301', 'T6-OPERATOR', 'OPERATOR',
    'INSUFFICIENT_GROUNDING'
  )$sql$,
  'same-reason confirmation succeeds'
);
SELECT ok(
  EXISTS (
    SELECT 1
    FROM app_private.failed_questions AS failures
    JOIN app_private.interaction_events AS events
      ON events.id = failures.interaction_event_id
    WHERE failures.id = '60000000-0000-4000-8000-000000000301'
      AND failures.status = 'REASON_CONFIRMED'
      AND failures.fallback_reason = 'INSUFFICIENT_GROUNDING'
      AND failures.candidate_eligible
      AND events.fallback_reason = 'INSUFFICIENT_GROUNDING'
  )
  AND EXISTS (
    SELECT 1 FROM app_private.audit_logs
    WHERE target_id = '60000000-0000-4000-8000-000000000301'
      AND action = 'FAILED_QUESTION_REASON_CONFIRMED'
      AND target_type = 'FAILED_QUESTION'
      AND actor_id = 'T6-OPERATOR'
      AND actor_role = 'OPERATOR'
      AND old_status = 'NEW'
      AND new_status = 'REASON_CONFIRMED'
      AND changed_field_names = '["status"]'::jsonb
      AND review_comment IS NULL
  ),
  'same reason updates status only and writes exact metadata audit'
);
SELECT throws_ok(
  $sql$SELECT app_api.confirm_failed_question_reason(
    '60000000-0000-4000-8000-000000000301', 'T6-OPERATOR', 'OPERATOR',
    'INSUFFICIENT_GROUNDING'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'duplicate confirmation is rejected'
);
SELECT throws_ok(
  $sql$UPDATE app_private.failed_questions
    SET status = 'NEW'
    WHERE id = '60000000-0000-4000-8000-000000000301'$sql$,
  'P0001', 'FAILED_EVENT_MISMATCH',
  'same-reason confirmed failure cannot revert to NEW'
);
SELECT is(
  (SELECT pg_catalog.count(*)::integer FROM app_private.audit_logs
   WHERE target_id = '60000000-0000-4000-8000-000000000301'),
  1,
  'duplicate confirmation still has exactly one audit row'
);

SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000302', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);
SELECT ok(
  EXISTS (
    SELECT 1
    FROM app_private.failed_questions AS failures
    JOIN app_private.interaction_events AS events
      ON events.id = failures.interaction_event_id
    WHERE failures.id = '60000000-0000-4000-8000-000000000302'
      AND failures.fallback_reason = 'INSUFFICIENT_GROUNDING'
      AND failures.candidate_eligible
      AND failures.status = 'REASON_CONFIRMED'
      AND events.fallback_reason = 'PERSONAL_LOOKUP'
  )
  AND EXISTS (
    SELECT 1 FROM app_private.audit_logs
    WHERE target_id = '60000000-0000-4000-8000-000000000302'
      AND changed_field_names =
        '["status","fallback_reason","candidate_eligible"]'::jsonb
  ),
  'corrected reason re-derives eligibility without changing event reason'
);

SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000303', 'T6-OPERATOR', 'OPERATOR',
  'PERSONAL_LOOKUP'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM app_private.failed_questions
    WHERE id = '60000000-0000-4000-8000-000000000303'
      AND fallback_reason = 'PERSONAL_LOOKUP'
      AND NOT candidate_eligible
      AND status = 'REASON_CONFIRMED'
  )
  AND EXISTS (
    SELECT 1 FROM app_private.audit_logs
    WHERE target_id = '60000000-0000-4000-8000-000000000303'
      AND changed_field_names = '["status","fallback_reason"]'::jsonb
  ),
  'reason-only correction records canonical actual changed fields'
);
SELECT throws_ok(
  $sql$UPDATE app_private.failed_questions
    SET status = 'NEW'
    WHERE id = '60000000-0000-4000-8000-000000000303'$sql$,
  'P0001', 'FAILED_EVENT_MISMATCH',
  'corrected unlinked failure cannot revert to NEW without parent reason match'
);

SELECT lives_ok(
  $sql$UPDATE app_private.interaction_events
    SET fallback_reason = fallback_reason
    WHERE id = '60000000-0000-4000-8000-000000000202'$sql$,
  'confirmed failure permits a parent-event no-op update'
);
SELECT throws_ok(
  $sql$UPDATE app_private.interaction_events
    SET fallback_reason = 'LEGAL_JUDGMENT'
    WHERE id = '60000000-0000-4000-8000-000000000202'$sql$,
  'P0001', 'FAILED_EVENT_IMMUTABLE',
  'confirmed failure forbids actual parent-event classification changes'
);

SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000305', 'T6-OPERATOR', 'OPERATOR',
  'PERSONAL_LOOKUP'
);

-- Candidate creation locks the failure and requires confirmed IG eligibility.
SELECT throws_ok(
  $sql$SELECT app_api.create_kb_candidate(
    '60000000-0000-4000-8000-000000000304', 'T6-OPERATOR', 'OPERATOR',
    'Synthetic NEW candidate', 'Synthetic generalized question',
    'BULKY_WASTE', 'Synthetic answer', '[]', '[]', NULL, NULL,
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t6/new', DATE '2026-07-16', NULL, 'OFFICIAL'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'candidate cannot be created from NEW'
);
SELECT throws_ok(
  $sql$SELECT app_api.create_kb_candidate(
    '60000000-0000-4000-8000-000000000305', 'T6-OPERATOR', 'OPERATOR',
    'Synthetic ineligible candidate', 'Synthetic generalized question',
    'BULKY_WASTE', 'Synthetic answer', '[]', '[]', NULL, NULL,
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t6/ineligible', DATE '2026-07-16', NULL, 'OFFICIAL'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE',
  'candidate cannot be created from corrected ineligible failure'
);
SELECT throws_ok(
  $sql$SELECT app_api.create_kb_candidate(
    '60000000-0000-4000-8000-000000000302', 'T6-APPROVER', 'APPROVER',
    'Synthetic role candidate', 'Synthetic generalized question',
    'BULKY_WASTE', 'Synthetic answer', '[]', '[]', NULL, NULL,
    'Synthetic department', 'Synthetic source',
    'https://example.invalid/t6/role', DATE '2026-07-16', NULL, 'OFFICIAL'
  )$sql$,
  'P1001', 'FORBIDDEN_ACTOR', 'only OPERATOR can create a candidate'
);
SELECT throws_ok(
  $sql$SELECT app_api.create_kb_candidate(
    '60000000-0000-4000-8000-000000000302', 'T6-OPERATOR', 'OPERATOR',
    'Synthetic incomplete candidate', 'Synthetic generalized question',
    'BULKY_WASTE', 'Synthetic answer', '[]', '[]', NULL, NULL,
    '   ', 'Synthetic source',
    'https://example.invalid/t6/incomplete', DATE '2026-07-16', NULL, 'OFFICIAL'
  )$sql$,
  'P1004', 'INCOMPLETE_CANDIDATE',
  'candidate creation maps incomplete content to stable P1004'
);

INSERT INTO task6_candidates
SELECT 'official', app_api.create_kb_candidate(
  '60000000-0000-4000-8000-000000000302', 'T6-OPERATOR', 'OPERATOR',
  'Synthetic official candidate', 'Synthetic generalized official question',
  'BULKY_WASTE', 'Synthetic official answer', '["Synthetic step"]',
  '["Synthetic document"]', 'Synthetic processing', 'Synthetic fee',
  'Synthetic department', 'Synthetic official source',
  'https://example.invalid/t6/official', DATE '2026-07-16',
  'Synthetic caution', 'OFFICIAL'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    WHERE result.label = 'official'
      AND candidates.review_status = 'DRAFTED'
      AND candidates.created_by = 'T6-OPERATOR'
      AND candidates.reviewed_by IS NULL
      AND candidates.review_comment IS NULL
      AND candidates.approved_at IS NULL
      AND candidates.activated_kb_id IS NULL
  )
  AND EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.audit_logs AS audit ON audit.target_id = result.candidate_id
    WHERE result.label = 'official'
      AND audit.action = 'CANDIDATE_CREATED'
      AND audit.target_type = 'KB_CANDIDATE'
      AND audit.actor_role = 'OPERATOR'
      AND audit.old_status IS NULL
      AND audit.new_status = 'DRAFTED'
      AND audit.changed_field_names = '["review_status"]'::jsonb
      AND audit.review_comment IS NULL
  ),
  'candidate creation writes DRAFTED state and exact metadata audit'
);
SELECT throws_ok(
  $sql$SELECT app_api.create_kb_candidate(
    '60000000-0000-4000-8000-000000000302', 'T6-OPERATOR', 'OPERATOR',
    'Synthetic duplicate', 'Synthetic generalized duplicate', 'BULKY_WASTE',
    'Synthetic answer', '[]', '[]', NULL, NULL, 'Synthetic department',
    'Synthetic source', 'https://example.invalid/t6/duplicate',
    DATE '2026-07-16', NULL, 'OFFICIAL'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'duplicate candidate is stable P1003'
);

-- Submission requires OPERATOR creator ownership, DRAFTED state, and complete
-- content. Successful submission writes exactly one state-only audit row.
SELECT throws_ok(
  $sql$SELECT app_api.submit_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-OPERATOR', 'APPROVER'
  )$sql$,
  'P1001', 'FORBIDDEN_ACTOR', 'only OPERATOR can submit a candidate'
);
SELECT throws_ok(
  $sql$SELECT app_api.submit_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-OTHER-OPERATOR', 'OPERATOR'
  )$sql$,
  'P1001', 'FORBIDDEN_ACTOR', 'only the creator can submit a candidate'
);
SELECT lives_ok(
  $sql$SELECT app_api.submit_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-OPERATOR', 'OPERATOR'
  )$sql$,
  'creator submits complete DRAFTED candidate'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    WHERE result.label = 'official'
      AND candidates.review_status = 'PENDING_APPROVAL'
      AND candidates.reviewed_by IS NULL
      AND candidates.review_comment IS NULL
      AND candidates.approved_at IS NULL
      AND candidates.activated_kb_id IS NULL
  )
  AND (
    SELECT pg_catalog.count(*) = 1
    FROM task6_candidates AS result
    JOIN app_private.audit_logs AS audit ON audit.target_id = result.candidate_id
    WHERE result.label = 'official'
      AND audit.action = 'CANDIDATE_SUBMITTED'
      AND audit.actor_role = 'OPERATOR'
      AND audit.old_status = 'DRAFTED'
      AND audit.new_status = 'PENDING_APPROVAL'
      AND audit.changed_field_names = '["review_status"]'::jsonb
  ),
  'submission writes pending state and exactly one metadata audit'
);
SELECT throws_ok(
  $sql$SELECT app_api.submit_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-OPERATOR', 'OPERATOR'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'duplicate submission is stable P1003'
);

-- Approval role, self-review, comment, origin, state, atomic writes, and return.
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-OPERATOR-2', 'OPERATOR', 'Synthetic review'
  )$sql$,
  'P1001', 'FORBIDDEN_ACTOR', 'OPERATOR cannot approve'
);
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-OPERATOR', 'APPROVER', 'Synthetic review'
  )$sql$,
  'P1002', 'SELF_REVIEW_FORBIDDEN', 'creator cannot approve own candidate'
);
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-APPROVER', 'APPROVER', '   '
  )$sql$,
  'P1004', 'INCOMPLETE_CANDIDATE', 'approval rejects blank review comment'
);
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-APPROVER', 'APPROVER', pg_catalog.repeat('x', 1001)
  )$sql$,
  'P1004', 'INCOMPLETE_CANDIDATE', 'approval rejects comment over 1000 chars'
);

SELECT is(
  app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-APPROVER', 'APPROVER', '  Synthetic approval accepted  '
  ),
  'KB-' || pg_catalog.upper(pg_catalog.replace(
    (SELECT candidate_id::text FROM task6_candidates WHERE label = 'official'),
    '-', ''
  )),
  'approval returns deterministic candidate-derived public ID'
);
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
SELECT ok(
  EXISTS (
    SELECT 1
    FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    JOIN app_private.kb_documents AS kb
      ON kb.id = candidates.activated_kb_id
    WHERE result.label = 'official'
      AND candidates.review_status = 'APPROVED'
      AND candidates.reviewed_by = 'T6-APPROVER'
      AND candidates.review_comment = 'Synthetic approval accepted'
      AND candidates.approved_at IS NOT NULL
      AND kb.public_id = 'KB-' || pg_catalog.upper(
        pg_catalog.replace(candidates.id::text, '-', '')
      )
      AND kb.status = 'ACTIVE'
      AND kb.data_origin = 'OFFICIAL'
      AND kb.created_by = candidates.created_by
      AND kb.approved_by = 'T6-APPROVER'
      AND kb.approved_at = candidates.approved_at
      AND kb.answer_summary = candidates.answer_summary
      AND kb.source_title = candidates.source_title
      AND kb.source_url = candidates.source_url
      AND kb.last_verified_at = candidates.last_verified_at
  )
  AND (
    SELECT pg_catalog.count(*) = 1
    FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    JOIN app_private.kb_question_examples AS questions
      ON questions.kb_document_id = candidates.activated_kb_id
    WHERE result.label = 'official'
      AND questions.question_example = candidates.representative_question
  )
  AND (
    SELECT pg_catalog.count(*) = 1
    FROM task6_candidates AS result
    JOIN app_private.audit_logs AS audit ON audit.target_id = result.candidate_id
    WHERE result.label = 'official'
      AND audit.action = 'CANDIDATE_APPROVED'
      AND audit.actor_id = 'T6-APPROVER'
      AND audit.actor_role = 'APPROVER'
      AND audit.old_status = 'PENDING_APPROVAL'
      AND audit.new_status = 'APPROVED'
      AND audit.changed_field_names =
        '["review_status","reviewed_by","review_comment","approved_at","activated_kb_id"]'::jsonb
      AND audit.review_comment = 'Synthetic approval accepted'
  ),
  'approval atomically writes one ACTIVE KB, question, link, state, and audit'
);
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'official'),
    'T6-APPROVER-2', 'APPROVER', 'Synthetic duplicate approval'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'duplicate approval is stable P1003'
);

-- Build MOCK, rejection, and DRAFTED candidates through the same interfaces.
SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000306', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);
SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000307', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);
SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000308', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);
SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000309', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);
SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000310', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);

INSERT INTO task6_candidates
SELECT 'mock', app_api.create_kb_candidate(
  '60000000-0000-4000-8000-000000000307', 'T6-OPERATOR', 'OPERATOR',
  'Synthetic mock candidate', 'Synthetic generalized mock question',
  'BULKY_WASTE', 'Synthetic mock answer', '[]', '[]', NULL, NULL,
  'Synthetic department', 'Synthetic mock source',
  'https://example.invalid/t6/mock', DATE '2026-07-16', NULL, 'MOCK'
);
SELECT app_api.submit_kb_candidate(
  (SELECT candidate_id FROM task6_candidates WHERE label = 'mock'),
  'T6-OPERATOR', 'OPERATOR'
);
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'mock'),
    'T6-APPROVER', 'APPROVER', 'Synthetic mock review'
  )$sql$,
  'P1005', 'DISALLOWED_ORIGIN', 'MOCK candidate cannot activate'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    WHERE result.label = 'mock'
      AND candidates.review_status = 'PENDING_APPROVAL'
      AND candidates.activated_kb_id IS NULL
  )
  AND NOT EXISTS (
    SELECT 1 FROM app_private.kb_documents
    WHERE public_id = 'KB-' || pg_catalog.upper(pg_catalog.replace(
      (SELECT candidate_id::text FROM task6_candidates WHERE label = 'mock'),
      '-', ''
    ))
  ),
  'failed MOCK approval leaves candidate and KB writes unchanged'
);

INSERT INTO task6_candidates
SELECT 'reject', app_api.create_kb_candidate(
  '60000000-0000-4000-8000-000000000308', 'T6-OPERATOR', 'OPERATOR',
  'Synthetic reject candidate', 'Synthetic generalized reject question',
  'BULKY_WASTE', 'Synthetic reject answer', '[]', '[]', NULL, NULL,
  'Synthetic department', 'Synthetic official source',
  'https://example.invalid/t6/reject', DATE '2026-07-16', NULL, 'OFFICIAL'
);
SELECT app_api.submit_kb_candidate(
  (SELECT candidate_id FROM task6_candidates WHERE label = 'reject'),
  'T6-OPERATOR', 'OPERATOR'
);
SELECT throws_ok(
  $sql$SELECT app_api.reject_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'reject'),
    'T6-OPERATOR-2', 'OPERATOR', 'Synthetic rejection'
  )$sql$,
  'P1001', 'FORBIDDEN_ACTOR', 'OPERATOR cannot reject'
);
SELECT throws_ok(
  $sql$SELECT app_api.reject_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'reject'),
    'T6-OPERATOR', 'APPROVER', 'Synthetic rejection'
  )$sql$,
  'P1002', 'SELF_REVIEW_FORBIDDEN', 'creator cannot reject own candidate'
);
SELECT throws_ok(
  $sql$SELECT app_api.reject_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'reject'),
    'T6-APPROVER', 'APPROVER', ' '
  )$sql$,
  'P1004', 'INCOMPLETE_CANDIDATE', 'rejection rejects blank review comment'
);
SELECT throws_ok(
  $sql$SELECT app_api.reject_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'reject'),
    'T6-APPROVER', 'APPROVER', pg_catalog.repeat('x', 1001)
  )$sql$,
  'P1004', 'INCOMPLETE_CANDIDATE', 'rejection rejects comment over 1000 chars'
);
SELECT lives_ok(
  $sql$SELECT app_api.reject_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'reject'),
    'T6-APPROVER', 'APPROVER', '  Synthetic rejection accepted  '
  )$sql$,
  'different APPROVER can reject with a trimmed comment'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    WHERE result.label = 'reject'
      AND candidates.review_status = 'REJECTED'
      AND candidates.reviewed_by = 'T6-APPROVER'
      AND candidates.review_comment = 'Synthetic rejection accepted'
      AND candidates.approved_at IS NULL
      AND candidates.activated_kb_id IS NULL
  )
  AND (
    SELECT pg_catalog.count(*) = 1
    FROM task6_candidates AS result
    JOIN app_private.audit_logs AS audit ON audit.target_id = result.candidate_id
    WHERE result.label = 'reject'
      AND audit.action = 'CANDIDATE_REJECTED'
      AND audit.actor_role = 'APPROVER'
      AND audit.old_status = 'PENDING_APPROVAL'
      AND audit.new_status = 'REJECTED'
      AND audit.changed_field_names =
        '["review_status","reviewed_by","review_comment"]'::jsonb
      AND audit.review_comment = 'Synthetic rejection accepted'
  ),
  'rejection writes terminal shape and exactly one metadata audit'
);

INSERT INTO task6_candidates
SELECT 'drafted', app_api.create_kb_candidate(
  '60000000-0000-4000-8000-000000000309', 'T6-OPERATOR', 'OPERATOR',
  'Synthetic drafted candidate', 'Synthetic generalized drafted question',
  'BULKY_WASTE', 'Synthetic drafted answer', '[]', '[]', NULL, NULL,
  'Synthetic department', 'Synthetic official source',
  'https://example.invalid/t6/drafted', DATE '2026-07-16', NULL, 'OFFICIAL'
);
SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'drafted'),
    'T6-APPROVER', 'APPROVER', 'Synthetic premature approval'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'approval requires pending state'
);
SELECT throws_ok(
  $sql$SELECT app_api.reject_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'drafted'),
    'T6-APPROVER', 'APPROVER', 'Synthetic premature rejection'
  )$sql$,
  'P1003', 'INVALID_WORKFLOW_STATE', 'rejection requires pending state'
);
SELECT throws_ok(
  $sql$UPDATE app_private.failed_questions
    SET status = 'NEW'
    WHERE id = '60000000-0000-4000-8000-000000000309'$sql$,
  'P0001', 'CANDIDATE_FAILURE_NOT_ELIGIBLE',
  'linked failure status cannot be changed to invalidate its candidate'
);

-- A deterministic public-ID collision forces the approval statement to fail;
-- all candidate/KB/question/audit work must remain atomic.
INSERT INTO task6_candidates
SELECT 'rollback', app_api.create_kb_candidate(
  '60000000-0000-4000-8000-000000000310', 'T6-OPERATOR', 'OPERATOR',
  'Synthetic rollback candidate', 'Synthetic generalized rollback question',
  'BULKY_WASTE', 'Synthetic rollback answer', '[]', '[]', NULL, NULL,
  'Synthetic department', 'Synthetic official source',
  'https://example.invalid/t6/rollback', DATE '2026-07-16', NULL, 'OFFICIAL'
);
SELECT app_api.submit_kb_candidate(
  (SELECT candidate_id FROM task6_candidates WHERE label = 'rollback'),
  'T6-OPERATOR', 'OPERATOR'
);
INSERT INTO app_private.kb_documents (
  public_id, data_origin, category, service_name, answer_summary,
  procedure_steps, required_documents, department, source_title, source_url,
  last_verified_at, status, created_by
) VALUES (
  'KB-' || pg_catalog.upper(pg_catalog.replace(
    (SELECT candidate_id::text FROM task6_candidates WHERE label = 'rollback'),
    '-', ''
  )),
  'OFFICIAL', 'BULKY_WASTE', 'Synthetic collision', 'Synthetic collision',
  '[]', '[]', 'Synthetic department', 'Synthetic source',
  'https://example.invalid/t6/collision', DATE '2026-07-16', 'DRAFT',
  'T6-OPERATOR'
);
DO $capture_collision$
DECLARE
  v_candidate_id uuid := (
    SELECT candidate_id FROM task6_candidates WHERE label = 'rollback'
  );
  v_comment constant text := 'Synthetic collision review';
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
    PERFORM app_api.approve_kb_candidate(
      v_candidate_id, 'T6-APPROVER', 'APPROVER', v_comment
    );
    INSERT INTO pg_temp.task6_error_diagnostics VALUES (
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
    INSERT INTO pg_temp.task6_error_diagnostics VALUES (
      v_state, v_message, v_detail, v_hint, v_context, v_schema, v_table,
      v_column, v_constraint, v_datatype
    );
  END;
END;
$capture_collision$;
SELECT ok(
  (
    SELECT pg_catalog.count(*) = 1
      AND pg_catalog.bool_and(
        diagnostics.returned_sqlstate = 'P1003'
        AND diagnostics.message_text = 'INVALID_WORKFLOW_STATE'
        AND COALESCE(diagnostics.exception_detail, '') = ''
        AND COALESCE(diagnostics.exception_hint, '') = ''
        AND COALESCE(diagnostics.schema_name, '') = ''
        AND COALESCE(diagnostics.table_name, '') = ''
        AND COALESCE(diagnostics.column_name, '') = ''
        AND COALESCE(diagnostics.constraint_name, '') = ''
        AND COALESCE(diagnostics.datatype_name, '') = ''
        AND pg_catalog.strpos(
          COALESCE(diagnostics.exception_context, ''),
          (SELECT candidate_id::text FROM task6_candidates
           WHERE label = 'rollback')
        ) = 0
        AND pg_catalog.strpos(
          pg_catalog.concat_ws(
            E'\n', diagnostics.exception_detail, diagnostics.exception_hint,
            diagnostics.exception_context, diagnostics.schema_name,
            diagnostics.table_name, diagnostics.column_name,
            diagnostics.constraint_name, diagnostics.datatype_name
          ),
          'KB-'
        ) = 0
      )
    FROM task6_error_diagnostics AS diagnostics
  ),
  'approval collision maps to nonleaking stable P1003 diagnostics'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    WHERE result.label = 'rollback'
      AND candidates.review_status = 'PENDING_APPROVAL'
      AND candidates.reviewed_by IS NULL
      AND candidates.review_comment IS NULL
      AND candidates.approved_at IS NULL
      AND candidates.activated_kb_id IS NULL
  )
  AND NOT EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.audit_logs AS audit ON audit.target_id = result.candidate_id
    WHERE result.label = 'rollback'
      AND audit.action = 'CANDIDATE_APPROVED'
  ),
  'failed approval rolls back candidate and approval audit changes'
);
TRUNCATE task6_error_diagnostics;

-- Inject a transaction-scoped audit failure after KB/question/candidate writes.
-- The trigger and helper are removed in this same test transaction.
SELECT app_api.confirm_failed_question_reason(
  '60000000-0000-4000-8000-000000000311', 'T6-OPERATOR', 'OPERATOR',
  'INSUFFICIENT_GROUNDING'
);
INSERT INTO task6_candidates
SELECT 'late-rollback', app_api.create_kb_candidate(
  '60000000-0000-4000-8000-000000000311', 'T6-OPERATOR', 'OPERATOR',
  'Synthetic late rollback candidate',
  'Synthetic generalized late rollback question', 'BULKY_WASTE',
  'Synthetic late rollback answer', '[]', '[]', NULL, NULL,
  'Synthetic department', 'Synthetic official source',
  'https://example.invalid/t6/late-rollback', DATE '2026-07-16',
  NULL, 'OFFICIAL'
);
SELECT app_api.submit_kb_candidate(
  (SELECT candidate_id FROM task6_candidates WHERE label = 'late-rollback'),
  'T6-OPERATOR', 'OPERATOR'
);

CREATE FUNCTION pg_temp.task6_test_fail_late_approval_audit()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $function$
BEGIN
  IF NEW.action = 'CANDIDATE_APPROVED'
     AND NEW.review_comment = 'Synthetic late-stage failure' THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P0001', MESSAGE = 'SYNTHETIC_LATE_APPROVAL_FAILURE';
  END IF;
  RETURN NEW;
END
$function$;
CREATE TRIGGER trg_task6_test_fail_late_approval_audit
BEFORE INSERT ON app_private.audit_logs
FOR EACH ROW
EXECUTE FUNCTION pg_temp.task6_test_fail_late_approval_audit();

SELECT throws_ok(
  $sql$SELECT app_api.approve_kb_candidate(
    (SELECT candidate_id FROM task6_candidates WHERE label = 'late-rollback'),
    'T6-APPROVER', 'APPROVER', 'Synthetic late-stage failure'
  )$sql$,
  'P0001', 'SYNTHETIC_LATE_APPROVAL_FAILURE',
  'late audit failure aborts approval after prior writes'
);

DROP TRIGGER trg_task6_test_fail_late_approval_audit
  ON app_private.audit_logs;
DROP FUNCTION pg_temp.task6_test_fail_late_approval_audit();

SELECT ok(
  EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.kb_candidates AS candidates
      ON candidates.id = result.candidate_id
    WHERE result.label = 'late-rollback'
      AND candidates.review_status = 'PENDING_APPROVAL'
      AND candidates.reviewed_by IS NULL
      AND candidates.review_comment IS NULL
      AND candidates.approved_at IS NULL
      AND candidates.activated_kb_id IS NULL
  )
  AND NOT EXISTS (
    SELECT 1 FROM app_private.kb_question_examples AS questions
    WHERE questions.question_example =
      'Synthetic generalized late rollback question'
  )
  AND NOT EXISTS (
    SELECT 1 FROM app_private.kb_documents AS kb
    WHERE kb.public_id = 'KB-' || pg_catalog.upper(pg_catalog.replace(
      (SELECT candidate_id::text FROM task6_candidates
       WHERE label = 'late-rollback'), '-', ''
    ))
  )
  AND NOT EXISTS (
    SELECT 1 FROM task6_candidates AS result
    JOIN app_private.audit_logs AS audit ON audit.target_id = result.candidate_id
    WHERE result.label = 'late-rollback'
      AND audit.action = 'CANDIDATE_APPROVED'
  ),
  'late failure rolls back KB, question, candidate link/state, and approval audit'
);

-- Audit action/status/role/field/comment shapes cannot be cross-combined.
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id,
    old_status, new_status, changed_field_names
  ) VALUES (
    'T6-APPROVER', 'APPROVER', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '60000000-0000-4000-8000-000000000999', NULL, 'DRAFTED',
    '["review_status"]'
  )$sql$,
  '23514', NULL, 'candidate-created audit requires OPERATOR role'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id,
    old_status, new_status, changed_field_names
  ) VALUES (
    'T6-OPERATOR', 'OPERATOR', 'CANDIDATE_APPROVED', 'KB_CANDIDATE',
    '60000000-0000-4000-8000-000000000999', 'PENDING_APPROVAL', 'APPROVED',
    '["review_status","reviewed_by","review_comment","approved_at","activated_kb_id"]'
  )$sql$,
  '23514', NULL, 'candidate-approved audit requires APPROVER and comment'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id,
    old_status, new_status, changed_field_names
  ) VALUES (
    'T6-OPERATOR', 'OPERATOR', 'FAILED_QUESTION_REASON_CONFIRMED',
    'KB_CANDIDATE', '60000000-0000-4000-8000-000000000999',
    'NEW', 'REASON_CONFIRMED', '["status"]'
  )$sql$,
  '23514', NULL, 'reason-confirmation audit requires failed-question target'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id,
    old_status, new_status, changed_field_names
  ) VALUES (
    'T6-OPERATOR', 'OPERATOR', 'CANDIDATE_SUBMITTED', 'KB_CANDIDATE',
    '60000000-0000-4000-8000-000000000999', 'DRAFTED', 'PENDING_APPROVAL',
    '["reviewed_by"]'
  )$sql$,
  '23514', NULL, 'candidate-submitted audit rejects wrong changed fields'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id,
    old_status, new_status, changed_field_names, review_comment
  ) VALUES (
    'T6-APPROVER', 'APPROVER', 'CANDIDATE_REJECTED', 'KB_CANDIDATE',
    '60000000-0000-4000-8000-000000000999', 'PENDING_APPROVAL', 'REJECTED',
    '["review_status","reviewed_by","review_comment"]',
    pg_catalog.repeat('x', 1001)
  )$sql$,
  '23514', NULL, 'audit review comment rejects more than 1000 characters'
);

SELECT results_eq(
  $actual$
    SELECT columns.column_name::text COLLATE "C"
    FROM information_schema.columns AS columns
    WHERE columns.table_schema = 'app_private'
      AND columns.table_name = 'audit_logs'
    ORDER BY columns.ordinal_position
  $actual$,
  $expected$
    SELECT expected.column_name COLLATE "C"
    FROM pg_catalog.unnest(ARRAY[
      'id', 'actor_id', 'actor_role', 'action', 'target_type', 'target_id',
      'old_status', 'new_status', 'changed_field_names', 'review_comment',
      'created_at'
    ]) AS expected(column_name)
  $expected$,
  'audit rows contain only approved metadata columns'
);

CREATE ROLE sejong_task6_backend_probe
  NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT sejong_backend TO sejong_task6_backend_probe WITH ADMIN FALSE;
GRANT sejong_backend TO sejong_task6_backend_probe WITH INHERIT TRUE;
GRANT sejong_backend TO sejong_task6_backend_probe WITH SET FALSE;
GRANT USAGE ON SCHEMA extensions TO sejong_task6_backend_probe;
GRANT INSERT ON task6_error_diagnostics TO sejong_task6_backend_probe;
DO $grant_probe_to_runner$
BEGIN
  EXECUTE pg_catalog.format(
    'GRANT sejong_task6_backend_probe TO %I WITH SET TRUE', CURRENT_USER
  );
END;
$grant_probe_to_runner$;

SET LOCAL ROLE sejong_task6_backend_probe;
SELECT throws_ok(
  $sql$UPDATE app_private.audit_logs SET new_status = new_status$sql$,
  '42501', NULL, 'backend cannot UPDATE audit rows'
);
SELECT throws_ok(
  $sql$DELETE FROM app_private.audit_logs$sql$,
  '42501', NULL, 'backend cannot DELETE audit rows'
);
RESET ROLE;

SELECT is(
  (
    SELECT pg_catalog.count(*)::integer
    FROM pg_catalog.pg_class AS relations
    JOIN pg_catalog.pg_namespace AS namespaces
      ON namespaces.oid = relations.relnamespace
    CROSS JOIN pg_catalog.unnest(ARRAY['INSERT', 'UPDATE', 'DELETE'])
      AS requested(privilege_name)
    WHERE namespaces.nspname = 'app_private'
      AND relations.relname IN ('failed_questions', 'kb_candidates', 'audit_logs')
      AND pg_catalog.has_table_privilege(
        'sejong_backend', relations.oid, requested.privilege_name
      )
  ),
  0,
  'backend retains no direct workflow-table write privilege'
);

-- Stable workflow exceptions never include candidate content.
SET LOCAL ROLE sejong_task6_backend_probe;
DO $capture_nonleak$
DECLARE
  v_actor_id constant text := 'SENTINEL_ACTOR_MUST_NOT_LEAK';
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
    PERFORM app_api.submit_kb_candidate(
      '60000000-0000-4000-8000-000000000999',
      v_actor_id, 'OPERATOR'
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
    INSERT INTO pg_temp.task6_error_diagnostics VALUES (
      v_state, v_message, v_detail, v_hint, v_context, v_schema, v_table,
      v_column, v_constraint, v_datatype
    );
  END;
END;
$capture_nonleak$;
RESET ROLE;
SELECT ok(
  (
    SELECT pg_catalog.count(*) = 1
      AND pg_catalog.bool_and(
        returned_sqlstate = 'P1003'
        AND message_text = 'INVALID_WORKFLOW_STATE'
        AND pg_catalog.strpos(pg_catalog.concat_ws(
          E'\n', returned_sqlstate, message_text, exception_detail,
          exception_hint, exception_context, schema_name, table_name,
          column_name, constraint_name, datatype_name
        ), 'SENTINEL_ACTOR_MUST_NOT_LEAK') = 0
      )
    FROM task6_error_diagnostics
  ),
  'stable workflow diagnostics contain no actor or record text'
);

SELECT * FROM finish();

ROLLBACK;
