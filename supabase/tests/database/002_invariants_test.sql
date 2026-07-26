BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;

SELECT plan(62);

-- Explicit transaction-scoped MOCK fixtures. OFFICIAL below means only the
-- provenance branch under test; no fixture survives this file's rollback.
INSERT INTO app_private.kb_documents (
  id, public_id, data_origin, category, service_name, answer_summary,
  procedure_steps, required_documents, department, source_title, source_url,
  last_verified_at, status, created_by, updated_at
) VALUES (
  '40000000-0000-4000-8000-000000000101',
  'T4-KB-DRAFT-MOCK',
  'MOCK',
  'BULKY_WASTE',
  'MOCK draft service',
  'MOCK draft summary',
  '[]'::jsonb,
  '[]'::jsonb,
  'MOCK department',
  'MOCK source',
  'https://example.invalid/t4/mock-kb',
  DATE '2026-07-16',
  'DRAFT',
  'MOCK-T4-OPERATOR',
  TIMESTAMPTZ '2000-01-01 00:00:00+00'
);

INSERT INTO app_private.offices (
  id, public_id, data_origin, region, office_name, address, phone,
  source_title, source_url, last_verified_at
) VALUES (
  '40000000-0000-4000-8000-000000000501',
  'T4-OFFICE-MOCK',
  'MOCK',
  '아름동',
  'MOCK office',
  'MOCK address',
  '000-000-0000',
  'MOCK source',
  'https://example.invalid/t4/mock-office',
  DATE '2026-07-16'
);

INSERT INTO app_private.office_service_mappings (office_id, intent, department_label)
VALUES (
  '40000000-0000-4000-8000-000000000501',
  'BULKY_WASTE',
  'MOCK department'
);

INSERT INTO app_private.interaction_events (
  id, intent, answer_status, fallback_reason, source_count, used_source_ids,
  response_time_ms, is_test, request_id
) VALUES
  (
    '40000000-0000-4000-8000-000000000201',
    'BULKY_WASTE', 'FALLBACK', 'PERSONAL_LOOKUP', 0, '[]'::jsonb,
    1, true, '40000000-0000-4000-8000-000000000211'
  ),
  (
    '40000000-0000-4000-8000-000000000202',
    'BULKY_WASTE', 'FALLBACK', 'INSUFFICIENT_GROUNDING', 0, '[]'::jsonb,
    1, true, '40000000-0000-4000-8000-000000000212'
  ),
  (
    '40000000-0000-4000-8000-000000000203',
    'BULKY_WASTE', 'FOLLOWUP', NULL, 0, '[]'::jsonb,
    1, true, '40000000-0000-4000-8000-000000000213'
  ),
  (
    '40000000-0000-4000-8000-000000000204',
    'OUT_OF_SCOPE', 'FALLBACK', 'OUT_OF_SCOPE', 0, '[]'::jsonb,
    1, true, '40000000-0000-4000-8000-000000000214'
  );

INSERT INTO app_private.failed_questions (
  id, interaction_event_id, masked_question, intent, fallback_reason,
  candidate_eligible, status, created_at, text_expires_at, updated_at
) VALUES
  (
    '40000000-0000-4000-8000-000000000301',
    '40000000-0000-4000-8000-000000000201',
    '[MASKED] MOCK personal lookup',
    'BULKY_WASTE', 'PERSONAL_LOOKUP', false, 'NEW',
    TIMESTAMPTZ '2026-01-01 00:00:00+00',
    TIMESTAMPTZ '2026-01-31 00:00:00+00',
    TIMESTAMPTZ '2000-01-01 00:00:00+00'
  ),
  (
    '40000000-0000-4000-8000-000000000302',
    '40000000-0000-4000-8000-000000000202',
    '[MASKED] MOCK insufficient grounding',
    'BULKY_WASTE', 'INSUFFICIENT_GROUNDING', true, 'REASON_CONFIRMED',
    TIMESTAMPTZ '2026-01-01 00:00:00+00',
    TIMESTAMPTZ '2026-01-31 00:00:00+00',
    TIMESTAMPTZ '2000-01-01 00:00:00+00'
  );

INSERT INTO app_private.kb_candidates (
  id, failed_question_id, title, representative_question, data_origin,
  category, answer_summary, procedure_steps, required_documents, department,
  source_title, source_url, last_verified_at, created_by, review_status,
  updated_at
) VALUES (
  '40000000-0000-4000-8000-000000000401',
  '40000000-0000-4000-8000-000000000302',
  'MOCK candidate',
  'MOCK generalized question',
  'MOCK',
  'BULKY_WASTE',
  'MOCK candidate summary',
  '[]'::jsonb,
  '[]'::jsonb,
  'MOCK department',
  'MOCK source',
  'https://example.invalid/t4/mock-candidate',
  DATE '2026-07-16',
  'MOCK-T4-OPERATOR',
  'DRAFTED',
  TIMESTAMPTZ '2000-01-01 00:00:00+00'
);

-- 1-7: trimmed, non-empty public IDs and required text.
SELECT throws_ok(
  $sql$INSERT INTO app_private.kb_documents (
    public_id, data_origin, category, service_name, answer_summary, department,
    source_title, source_url, last_verified_at, created_by
  ) VALUES (
    '   ', 'MOCK', 'BULKY_WASTE', 'MOCK service', 'MOCK summary',
    'MOCK department', 'MOCK source', 'https://example.invalid/t4/blank-id',
    DATE '2026-07-16', 'MOCK-T4-OPERATOR'
  )$sql$,
  '23514', NULL, 'KB public_id rejects whitespace only'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.kb_documents (
    public_id, data_origin, category, service_name, answer_summary, department,
    source_title, source_url, last_verified_at, created_by
  ) VALUES (
    'T4-KB-BLANK-TEXT', 'MOCK', 'BULKY_WASTE', '   ', 'MOCK summary',
    'MOCK department', 'MOCK source', 'https://example.invalid/t4/blank-text',
    DATE '2026-07-16', 'MOCK-T4-OPERATOR'
  )$sql$,
  '23514', NULL, 'KB required text rejects whitespace only'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.kb_question_examples (
    kb_document_id, question_example
  ) VALUES ('40000000-0000-4000-8000-000000000101', '   ')$sql$,
  '23514', NULL, 'question example rejects whitespace only'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.offices (
    public_id, data_origin, region, office_name, address, phone,
    source_title, source_url, last_verified_at
  ) VALUES (
    '   ', 'MOCK', '아름동', 'MOCK office', 'MOCK address', '000',
    'MOCK source', 'https://example.invalid/t4/blank-office-id', DATE '2026-07-16'
  )$sql$,
  '23514', NULL, 'office public_id rejects whitespace only'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.offices (
    public_id, data_origin, region, office_name, address, phone,
    source_title, source_url, last_verified_at
  ) VALUES (
    'T4-OFFICE-BLANK-TEXT', 'MOCK', '아름동', '   ', 'MOCK address',
    '000', 'MOCK source', 'https://example.invalid/t4/blank-office-text',
    DATE '2026-07-16'
  )$sql$,
  '23514', NULL, 'office required text rejects whitespace only'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_candidates
    SET title = '   '
    WHERE id = '40000000-0000-4000-8000-000000000401'$sql$,
  '23514', NULL, 'candidate required text rejects whitespace only'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    '   ', 'OPERATOR', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '["review_status"]'::jsonb
  )$sql$,
  '23514', NULL, 'audit required text rejects whitespace only'
);

-- 8-15: procedure/document JSON arrays contain only trimmed non-empty strings.
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET procedure_steps = '{"step":"MOCK"}'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'procedure_steps rejects a non-array'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET procedure_steps = '["MOCK", 1]'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'procedure_steps rejects a non-string element'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET procedure_steps = '["   "]'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'procedure_steps rejects an empty string element'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET required_documents = 'null'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'required_documents rejects a non-array'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET required_documents = '[true]'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'required_documents rejects a non-string element'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET required_documents = '[""]'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'required_documents rejects an empty string element'
);
SELECT lives_ok(
  $sql$UPDATE app_private.kb_documents
    SET procedure_steps = '[]'::jsonb, required_documents = '[]'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  'empty procedure and document arrays are valid'
);
SELECT lives_ok(
  $sql$UPDATE app_private.kb_documents
    SET procedure_steps = '["MOCK step"]'::jsonb,
        required_documents = '["MOCK document"]'::jsonb
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  'trimmed non-empty string arrays are valid'
);

-- 16-19: category, region, mapping intent, and selected region allowlists.
SELECT throws_ok(
  $sql$UPDATE app_private.kb_documents
    SET category = 'OUT_OF_SCOPE'
    WHERE id = '40000000-0000-4000-8000-000000000101'$sql$,
  '23514', NULL, 'unsupported KB category is rejected'
);
SELECT throws_ok(
  $sql$UPDATE app_private.offices
    SET region = '지원하지않는지역'
    WHERE id = '40000000-0000-4000-8000-000000000501'$sql$,
  '23514', NULL, 'unsupported office region is rejected'
);
SELECT throws_ok(
  $sql$UPDATE app_private.office_service_mappings
    SET intent = 'UNKNOWN'
    WHERE office_id = '40000000-0000-4000-8000-000000000501'
      AND intent = 'BULKY_WASTE'$sql$,
  '23514', NULL, 'unsupported office mapping intent is rejected'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    selected_region, is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SYSTEM_ERROR', 0, '[]'::jsonb, 1,
    '지원하지않는지역', true,
    '40000000-0000-4000-8000-000000000219'
  )$sql$,
  '23514', NULL, 'unsupported selected region is rejected'
);

-- 20-24: ACTIVE is approved, OFFICIAL, and has a final-state question.
SELECT throws_ok(
  $sql$INSERT INTO app_private.kb_documents (
    public_id, data_origin, category, service_name, answer_summary, department,
    source_title, source_url, last_verified_at, status, created_by
  ) VALUES (
    'T4-KB-ACTIVE-NO-APPROVAL', 'OFFICIAL', 'BULKY_WASTE', 'MOCK service',
    'MOCK summary', 'MOCK department', 'MOCK source',
    'https://example.invalid/t4/no-approval', DATE '2026-07-16', 'ACTIVE',
    'MOCK-T4-OPERATOR'
  )$sql$,
  '23514', NULL, 'ACTIVE without approval fields is rejected'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.kb_documents (
    public_id, data_origin, category, service_name, answer_summary, department,
    source_title, source_url, last_verified_at, status, created_by,
    approved_by, approved_at
  ) VALUES (
    'T4-KB-ACTIVE-MOCK', 'MOCK', 'BULKY_WASTE', 'MOCK service', 'MOCK summary',
    'MOCK department', 'MOCK source', 'https://example.invalid/t4/mock-active',
    DATE '2026-07-16', 'ACTIVE', 'MOCK-T4-OPERATOR', 'MOCK-T4-APPROVER', now()
  )$sql$,
  '23514', NULL, 'ACTIVE with MOCK provenance is rejected'
);
SELECT throws_ok(
  $sql$DO $block$
  BEGIN
    INSERT INTO app_private.kb_documents (
      id, public_id, data_origin, category, service_name, answer_summary,
      department, source_title, source_url, last_verified_at, status,
      created_by, approved_by, approved_at
    ) VALUES (
      '40000000-0000-4000-8000-000000000111',
      'T4-KB-ACTIVE-NO-QUESTION', 'OFFICIAL', 'BULKY_WASTE', 'MOCK service',
      'MOCK summary', 'MOCK department', 'MOCK official source',
      'https://example.invalid/t4/no-question', DATE '2026-07-16', 'ACTIVE',
      'MOCK-T4-OPERATOR', 'MOCK-T4-APPROVER', now()
    );
    SET CONSTRAINTS ALL IMMEDIATE;
  END
  $block$$sql$,
  'P0001',
  'KB_ACTIVE_QUESTION_REQUIRED',
  'ACTIVE without a question fails at the deferred boundary'
);
SELECT lives_ok(
  $sql$DO $block$
  BEGIN
    INSERT INTO app_private.kb_documents (
      id, public_id, data_origin, category, service_name, answer_summary,
      department, source_title, source_url, last_verified_at, status, created_by
    ) VALUES (
      '40000000-0000-4000-8000-000000000120',
      'T4-KB-ACTIVE-OFFICIAL', 'OFFICIAL', 'BULKY_WASTE', 'MOCK official service',
      'MOCK official summary', 'MOCK department', 'MOCK official source',
      'https://example.invalid/t4/official-active', DATE '2026-07-16', 'DRAFT',
      'MOCK-T4-OPERATOR'
    );
    INSERT INTO app_private.kb_question_examples (
      id, kb_document_id, question_example
    ) VALUES (
      '40000000-0000-4000-8000-000000000121',
      '40000000-0000-4000-8000-000000000120',
      'MOCK generalized active question'
    );
    UPDATE app_private.kb_documents
    SET status = 'ACTIVE',
        approved_by = 'MOCK-T4-APPROVER',
        approved_at = now()
    WHERE id = '40000000-0000-4000-8000-000000000120';
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
  END
  $block$$sql$,
  'ACTIVE OFFICIAL with a question is valid at transaction end'
);
SELECT throws_ok(
  $sql$DO $block$
  BEGIN
    DELETE FROM app_private.kb_question_examples
    WHERE id = '40000000-0000-4000-8000-000000000121';
    SET CONSTRAINTS ALL IMMEDIATE;
  END
  $block$$sql$,
  'P0001',
  'KB_ACTIVE_QUESTION_REQUIRED',
  'deleting the final ACTIVE question fails at the deferred boundary'
);

-- 25-32: interaction sources are shaped, counted, unique, and grounded.
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 0, '[]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000225'
  )$sql$,
  '23514', NULL, 'SUCCESS without sources is rejected'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 1, '["T4-KB-DRAFT-MOCK"]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000226'
  )$sql$,
  'P0001',
  'EVENT_SOURCE_NOT_ACTIVE_OFFICIAL',
  'SUCCESS with a non-ACTIVE or MOCK source is rejected'
);
SELECT lives_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 1, '["T4-KB-ACTIVE-OFFICIAL"]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000227'
  )$sql$,
  'SUCCESS with one ACTIVE OFFICIAL source is valid'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 2, '["T4-KB-ACTIVE-OFFICIAL"]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000228'
  )$sql$,
  '23514', NULL, 'source_count must equal the source array length'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 2,
    '["T4-KB-ACTIVE-OFFICIAL", "T4-KB-ACTIVE-OFFICIAL"]'::jsonb,
    1, true, '40000000-0000-4000-8000-000000000229'
  )$sql$,
  '23514', NULL, 'used source IDs must be unique'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 1, '["   "]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000230'
  )$sql$,
  '23514', NULL, 'used source IDs reject empty strings'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 1, '[1]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000231'
  )$sql$,
  '23514', NULL, 'used source IDs reject non-string elements'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, source_count, used_source_ids, response_time_ms,
    is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'SUCCESS', 1, '{"id":"T4-KB-ACTIVE-OFFICIAL"}'::jsonb,
    1, true, '40000000-0000-4000-8000-000000000232'
  )$sql$,
  '23514', NULL, 'used source IDs reject a non-array'
);

-- 33-40: failure/candidate lineage, eligibility, expiry, and status subsets.
SELECT throws_ok(
  $sql$INSERT INTO app_private.interaction_events (
    intent, answer_status, fallback_reason, source_count, used_source_ids,
    response_time_ms, is_test, request_id
  ) VALUES (
    'BULKY_WASTE', 'FOLLOWUP', 'LEGAL_JUDGMENT', 0, '[]'::jsonb, 1, true,
    '40000000-0000-4000-8000-000000000233'
  )$sql$,
  '23514', NULL, 'FOLLOWUP with a fallback reason is rejected'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.failed_questions (
    interaction_event_id, masked_question, intent, fallback_reason,
    candidate_eligible
  ) VALUES (
    '40000000-0000-4000-8000-000000000203',
    '[MASKED] MOCK followup', 'BULKY_WASTE', 'LEGAL_JUDGMENT', false
  )$sql$,
  'P0001',
  'FAILED_EVENT_MISMATCH',
  'FOLLOWUP cannot have a failed question row'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.failed_questions (
    interaction_event_id, masked_question, intent, fallback_reason,
    candidate_eligible
  ) VALUES (
    '40000000-0000-4000-8000-000000000204',
    '[MASKED] MOCK out of scope', 'BULKY_WASTE', 'LEGAL_JUDGMENT', false
  )$sql$,
  'P0001',
  'FAILED_EVENT_MISMATCH',
  'OUT_OF_SCOPE cannot retain a failed-question text row'
);
SELECT throws_ok(
  $sql$UPDATE app_private.failed_questions
    SET candidate_eligible = true
    WHERE id = '40000000-0000-4000-8000-000000000301'$sql$,
  '23514', NULL, 'only INSUFFICIENT_GROUNDING can be candidate eligible'
);
SELECT throws_ok(
  $sql$UPDATE app_private.failed_questions
    SET text_expires_at = created_at + interval '29 days'
    WHERE id = '40000000-0000-4000-8000-000000000301'$sql$,
  '23514', NULL, 'failure text expiry must be exactly thirty days'
);
SELECT ok(
  (
    SELECT text_expires_at = created_at + interval '30 days'
    FROM app_private.failed_questions
    WHERE id = '40000000-0000-4000-8000-000000000301'
  ),
  'valid failure text expiry is exactly thirty days'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.kb_candidates (
    failed_question_id, title, representative_question, data_origin, category,
    answer_summary, department, source_title, source_url, last_verified_at,
    created_by
  ) VALUES (
    '40000000-0000-4000-8000-000000000301', 'MOCK invalid candidate',
    'MOCK generalized', 'MOCK', 'BULKY_WASTE', 'MOCK summary',
    'MOCK department', 'MOCK source',
    'https://example.invalid/t4/ineligible-candidate', DATE '2026-07-16',
    'MOCK-T4-OPERATOR'
  )$sql$,
  'P0001',
  'CANDIDATE_FAILURE_NOT_ELIGIBLE',
  'candidate must reference an eligible INSUFFICIENT_GROUNDING failure'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM app_private.kb_candidates
    WHERE id = '40000000-0000-4000-8000-000000000401'
      AND failed_question_id = '40000000-0000-4000-8000-000000000302'
  ),
  'candidate referencing an eligible failure is valid'
);
SELECT throws_ok(
  $sql$UPDATE app_private.failed_questions
    SET status = 'DRAFTED'
    WHERE id = '40000000-0000-4000-8000-000000000301'$sql$,
  '23514', NULL, 'failed question rejects candidate-only statuses'
);
SELECT throws_ok(
  $sql$UPDATE app_private.kb_candidates
    SET review_status = 'NEW'
    WHERE id = '40000000-0000-4000-8000-000000000401'$sql$,
  '23514', NULL, 'candidate rejects failure-only statuses'
);

-- 41-48: audit metadata has fixed action/target/changed-field allowlists.
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'UNAPPROVED_ACTION', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '["review_status"]'::jsonb
  )$sql$,
  '23514', NULL, 'audit action is allowlisted'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_CREATED', 'UNAPPROVED_TARGET',
    '40000000-0000-4000-8000-000000000401', '["review_status"]'::jsonb
  )$sql$,
  '23514', NULL, 'audit target type is allowlisted'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '{}'::jsonb
  )$sql$,
  '23514', NULL, 'audit changed fields reject a non-array'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '[1]'::jsonb
  )$sql$,
  '23514', NULL, 'audit changed fields reject non-string elements'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '["   "]'::jsonb
  )$sql$,
  '23514', NULL, 'audit changed fields reject empty strings'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '["answer_summary"]'::jsonb
  )$sql$,
  '23514', NULL, 'audit changed fields reject names outside the metadata allowlist'
);
SELECT throws_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_CREATED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', '[]'::jsonb
  )$sql$,
  '23514', NULL, 'audit changed fields cannot be empty'
);
SELECT lives_ok(
  $sql$INSERT INTO app_private.audit_logs (
    actor_id, actor_role, action, target_type, target_id, old_status, new_status,
    changed_field_names
  ) VALUES (
    'MOCK-T4-ACTOR', 'OPERATOR', 'CANDIDATE_SUBMITTED', 'KB_CANDIDATE',
    '40000000-0000-4000-8000-000000000401', 'DRAFTED', 'PENDING_APPROVAL',
    '["review_status"]'::jsonb
  )$sql$,
  'valid allowlisted audit metadata is accepted'
);

-- 49-54: exactly the three mutable domain tables receive updated_at triggers.
SELECT is(
  (
    SELECT count(*)::integer
    FROM pg_catalog.pg_trigger AS triggers
    JOIN pg_catalog.pg_class AS tables ON tables.oid = triggers.tgrelid
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = tables.relnamespace
    JOIN pg_catalog.pg_proc AS functions ON functions.oid = triggers.tgfoid
    WHERE namespaces.nspname = 'app_private'
      AND NOT triggers.tgisinternal
      AND functions.proname = 'set_updated_at'
      AND tables.relname = ANY (
        ARRAY['kb_documents', 'failed_questions', 'kb_candidates']
      )
  ),
  3,
  'set_updated_at is attached to exactly the three approved mutable tables'
);

UPDATE app_private.kb_documents
SET service_name = 'MOCK updated service'
WHERE id = '40000000-0000-4000-8000-000000000101';
SELECT ok(
  (
    SELECT updated_at > TIMESTAMPTZ '2000-01-01 00:00:00+00'
    FROM app_private.kb_documents
    WHERE id = '40000000-0000-4000-8000-000000000101'
  ),
  'KB update refreshes updated_at'
);

UPDATE app_private.failed_questions
SET masked_question = '[MASKED] MOCK personal lookup updated'
WHERE id = '40000000-0000-4000-8000-000000000301';
SELECT ok(
  (
    SELECT updated_at > TIMESTAMPTZ '2000-01-01 00:00:00+00'
    FROM app_private.failed_questions
    WHERE id = '40000000-0000-4000-8000-000000000301'
  ),
  'failed-question update refreshes updated_at'
);

UPDATE app_private.kb_candidates
SET title = 'MOCK candidate updated'
WHERE id = '40000000-0000-4000-8000-000000000401';
SELECT ok(
  (
    SELECT updated_at > TIMESTAMPTZ '2000-01-01 00:00:00+00'
    FROM app_private.kb_candidates
    WHERE id = '40000000-0000-4000-8000-000000000401'
  ),
  'candidate update refreshes updated_at'
);

SELECT is(
  (
    SELECT count(*)::integer
    FROM pg_catalog.pg_trigger AS triggers
    JOIN pg_catalog.pg_class AS tables ON tables.oid = triggers.tgrelid
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = tables.relnamespace
    JOIN pg_catalog.pg_proc AS functions ON functions.oid = triggers.tgfoid
    WHERE namespaces.nspname = 'app_private'
      AND NOT triggers.tgisinternal
      AND functions.proname = 'set_updated_at'
      AND tables.relname NOT IN (
        'kb_documents', 'failed_questions', 'kb_candidates', 'chat_idempotency',
        'civic_scope_gaps'
      )
  ),
  0,
  'set_updated_at is absent outside the five approved mutable tables'
);

SELECT is(
  (
    SELECT count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_private'
      AND functions.proname IN (
        'is_nonempty_text',
        'is_text_array',
        'is_unique_text_array',
        'is_allowed_audit_changed_fields',
        'set_updated_at',
        'validate_interaction_event_sources',
        'validate_failed_question_event',
        'validate_interaction_event_failure',
        'validate_kb_candidate_failure',
        'validate_failed_question_candidate',
        'lock_kb_question_parents',
        'validate_active_kb_question'
      )
      AND functions.proconfig = CASE functions.proname
        WHEN 'validate_active_kb_question' THEN
          ARRAY['search_path=pg_catalog, pg_temp']::text[]
        ELSE ARRAY['search_path=pg_catalog']::text[]
      END
  ),
  12,
  'all twelve Task 4 functions use their approved fixed search paths'
);

SELECT is(
  (
    SELECT count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    JOIN pg_catalog.pg_language AS languages ON languages.oid = functions.prolang
    WHERE namespaces.nspname = 'app_private'
      AND functions.proname IN (
        'is_nonempty_text',
        'is_text_array',
        'is_unique_text_array',
        'is_allowed_audit_changed_fields'
      )
      AND languages.lanname = 'sql'
      AND functions.provolatile = 'i'
      AND functions.proisstrict
  ),
  4,
  'all four SQL validators are immutable and strict'
);

SELECT ok(
  (
    SELECT count(*) = 4
      AND pg_catalog.bool_and(
        CASE triggers.tgname
          WHEN 'trg_failed_questions_validate_event' THEN columns.names =
            CASE WHEN pg_catalog.to_regprocedure(
              'app_api.confirm_failed_question_reason(uuid,text,text,text)'
            ) IS NULL THEN ARRAY[
              'fallback_reason', 'intent', 'interaction_event_id'
            ]::text[] ELSE ARRAY[
              'fallback_reason', 'intent', 'interaction_event_id', 'status'
            ]::text[] END
          WHEN 'trg_interaction_events_validate_failure' THEN columns.names = ARRAY[
            'answer_status', 'fallback_reason', 'intent'
          ]::text[]
          WHEN 'trg_kb_candidates_validate_failure' THEN columns.names = ARRAY[
            'failed_question_id'
          ]::text[]
          WHEN 'trg_failed_questions_validate_candidate' THEN columns.names = ARRAY[
            'candidate_eligible', 'fallback_reason'
          ]::text[]
          ELSE false
        END
      )
    FROM pg_catalog.pg_trigger AS triggers
    JOIN pg_catalog.pg_class AS tables ON tables.oid = triggers.tgrelid
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = tables.relnamespace
    CROSS JOIN LATERAL (
      SELECT pg_catalog.array_agg(attributes.attname::text ORDER BY attributes.attname) AS names
      FROM pg_catalog.unnest(triggers.tgattr::smallint[]) AS numbers(attnum)
      JOIN pg_catalog.pg_attribute AS attributes
        ON attributes.attrelid = tables.oid
        AND attributes.attnum = numbers.attnum
    ) AS columns
    WHERE namespaces.nspname = 'app_private'
      AND NOT triggers.tgisinternal
      AND triggers.tgname IN (
        'trg_failed_questions_validate_event',
        'trg_interaction_events_validate_failure',
        'trg_kb_candidates_validate_failure',
        'trg_failed_questions_validate_candidate'
      )
  )
  AND pg_catalog.pg_get_functiondef(
    'app_private.validate_interaction_event_failure()'::regprocedure
  ) !~* 'FOR[[:space:]]+UPDATE'
  AND pg_catalog.pg_get_functiondef(
    'app_private.validate_failed_question_candidate()'::regprocedure
  ) !~* 'FOR[[:space:]]+UPDATE',
  'lineage UPDATE triggers are column scoped and reverse validators do not lock children'
);

SELECT ok(
  pg_catalog.pg_get_functiondef(
    'app_private.lock_kb_question_parents()'::regprocedure
  ) ~ 'current_setting\(''transaction_isolation''\)'
  AND pg_catalog.pg_get_functiondef(
    'app_private.lock_kb_question_parents()'::regprocedure
  ) LIKE '%KB_QUESTION_WRITE_REQUIRES_READ_COMMITTED%',
  'question parent lock fails closed outside read committed isolation'
);

SELECT ok(
  pg_catalog.pg_get_functiondef(
    'app_private.validate_active_kb_question()'::regprocedure
  ) ~ 'current_setting\(''transaction_isolation''\)'
  AND pg_catalog.pg_get_functiondef(
    'app_private.validate_active_kb_question()'::regprocedure
  ) LIKE '%KB_ACTIVE_TRANSITION_REQUIRES_READ_COMMITTED%',
  'parent ACTIVE transition fails closed outside read committed isolation'
);

SELECT is(
  (
    SELECT count(*)::integer
    FROM pg_catalog.pg_proc AS functions
    JOIN pg_catalog.pg_namespace AS namespaces ON namespaces.oid = functions.pronamespace
    WHERE namespaces.nspname = 'app_private'
      AND functions.proname IN (
        'validate_interaction_event_sources',
        'validate_failed_question_event',
        'validate_interaction_event_failure',
        'validate_kb_candidate_failure',
        'validate_failed_question_candidate'
      )
      AND pg_catalog.pg_get_functiondef(functions.oid)
        ~ 'current_setting\(''transaction_isolation''\)'
      AND pg_catalog.pg_get_functiondef(functions.oid)
        LIKE '%LINEAGE_WRITE_REQUIRES_READ_COMMITTED%'
  ),
  5,
  'all five cross-table lineage validators fail closed outside read committed isolation'
);

-- Remove every transaction-scoped fixture, force deferred checks, and prove none remain.
DELETE FROM app_private.audit_logs
WHERE target_id = '40000000-0000-4000-8000-000000000401';
DELETE FROM app_private.kb_candidates
WHERE source_url LIKE 'https://example.invalid/t4/%';
DELETE FROM app_private.failed_questions
WHERE interaction_event_id IN (
  SELECT id
  FROM app_private.interaction_events
  WHERE request_id BETWEEN
    '40000000-0000-4000-8000-000000000211'::uuid
    AND '40000000-0000-4000-8000-000000000233'::uuid
);
DELETE FROM app_private.interaction_events
WHERE request_id BETWEEN
  '40000000-0000-4000-8000-000000000211'::uuid
  AND '40000000-0000-4000-8000-000000000233'::uuid;
DELETE FROM app_private.offices
WHERE source_url LIKE 'https://example.invalid/t4/%';
DELETE FROM app_private.kb_documents
WHERE source_url LIKE 'https://example.invalid/t4/%';
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;

SELECT is(
  (
    (
      SELECT count(*) FROM app_private.audit_logs
      WHERE target_id = '40000000-0000-4000-8000-000000000401'
    )
    + (
      SELECT count(*) FROM app_private.kb_candidates
      WHERE source_url LIKE 'https://example.invalid/t4/%'
    )
    + (
      SELECT count(*)
      FROM app_private.failed_questions AS failures
      JOIN app_private.interaction_events AS events
        ON events.id = failures.interaction_event_id
      WHERE events.request_id BETWEEN
        '40000000-0000-4000-8000-000000000211'::uuid
        AND '40000000-0000-4000-8000-000000000233'::uuid
    )
    + (
      SELECT count(*)
      FROM app_private.interaction_events
      WHERE request_id BETWEEN
        '40000000-0000-4000-8000-000000000211'::uuid
        AND '40000000-0000-4000-8000-000000000233'::uuid
    )
    + (
      SELECT count(*) FROM app_private.offices
      WHERE source_url LIKE 'https://example.invalid/t4/%'
    )
    + (
      SELECT count(*) FROM app_private.kb_documents
      WHERE source_url LIKE 'https://example.invalid/t4/%'
    )
  )::integer,
  0,
  'all Task 4 fixtures are removed before transaction rollback'
);

SELECT * FROM finish();

ROLLBACK;
