-- Logical projection of executable migration baseline 0.4.0-local.
--
-- This file is for human review only. It is not executable authority and must not
-- be run to create, migrate, or recover a database. The ordered authority is
-- supabase/migrations/*.sql; disposable-local compensation is
-- database/rollbacks/*.rollback.sql in reverse timestamp order.
--
-- This projection intentionally omits helper/capability/trigger functions, RLS,
-- policies, owners, GRANT/REVOKE statements, and cross-row trigger bodies. Those
-- security boundaries are defined and tested only in the executable lineage.

CREATE TYPE app_private.intent_code AS ENUM (
  'MOVE_IN_RESIDENT_REGISTRATION',
  'CERTIFICATE_ISSUANCE',
  'BULKY_WASTE',
  'LOCAL_TAX_GENERAL',
  'OUT_OF_SCOPE',
  'UNKNOWN'
);

CREATE TYPE app_private.answer_status AS ENUM (
  'SUCCESS',
  'FOLLOWUP',
  'FALLBACK',
  'SYSTEM_ERROR'
);

CREATE TYPE app_private.fallback_reason AS ENUM (
  'INSUFFICIENT_GROUNDING',
  'PERSONAL_LOOKUP',
  'LEGAL_JUDGMENT',
  'OUT_OF_SCOPE'
);

CREATE TYPE app_private.kb_status AS ENUM (
  'DRAFT',
  'PENDING',
  'ACTIVE',
  'REJECTED',
  'RETIRED'
);

CREATE TYPE app_private.candidate_status AS ENUM (
  'NEW',
  'REASON_CONFIRMED',
  'DRAFTED',
  'PENDING_APPROVAL',
  'APPROVED',
  'REJECTED'
);

CREATE TYPE app_private.admin_role AS ENUM ('OPERATOR', 'APPROVER');
CREATE TYPE app_private.data_origin AS ENUM ('OFFICIAL', 'MOCK');

CREATE TABLE app_private.kb_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  public_id text UNIQUE NOT NULL,
  data_origin app_private.data_origin NOT NULL,
  category app_private.intent_code NOT NULL,
  service_name text NOT NULL,
  answer_summary text NOT NULL,
  procedure_steps jsonb NOT NULL DEFAULT '[]'::jsonb,
  required_documents jsonb NOT NULL DEFAULT '[]'::jsonb,
  processing_time text,
  fee text,
  department text NOT NULL,
  source_title text NOT NULL,
  source_url text NOT NULL,
  last_verified_at date NOT NULL,
  caution text,
  status app_private.kb_status NOT NULL DEFAULT 'DRAFT',
  created_by text NOT NULL,
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (category IN (
    'MOVE_IN_RESIDENT_REGISTRATION',
    'CERTIFICATE_ISSUANCE',
    'BULKY_WASTE',
    'LOCAL_TAX_GENERAL'
  )),
  CHECK (
    status <> 'ACTIVE'
    OR (
      data_origin = 'OFFICIAL'
      AND approved_by IS NOT NULL
      AND approved_at IS NOT NULL
    )
  ),
  CHECK (approved_by IS NULL OR approved_by <> created_by)
);

CREATE TABLE app_private.kb_question_examples (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kb_document_id uuid NOT NULL
    REFERENCES app_private.kb_documents(id) ON DELETE CASCADE,
  question_example text NOT NULL,
  normalized_text text,
  UNIQUE (kb_document_id, question_example)
);

CREATE TABLE app_private.offices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  public_id text UNIQUE NOT NULL,
  data_origin app_private.data_origin NOT NULL,
  region text NOT NULL CHECK (region IN ('아름동', '도담동', '조치원읍')),
  office_name text NOT NULL,
  address text NOT NULL,
  phone text NOT NULL,
  opening_hours text,
  map_url text,
  source_title text NOT NULL,
  source_url text NOT NULL,
  last_verified_at date NOT NULL,
  is_official boolean
    GENERATED ALWAYS AS (
      data_origin = 'OFFICIAL'::app_private.data_origin
    ) STORED,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_private.office_service_mappings (
  office_id uuid NOT NULL
    REFERENCES app_private.offices(id) ON DELETE CASCADE,
  intent app_private.intent_code NOT NULL,
  department_label text,
  PRIMARY KEY (office_id, intent),
  CHECK (intent IN (
    'MOVE_IN_RESIDENT_REGISTRATION',
    'CERTIFICATE_ISSUANCE',
    'BULKY_WASTE',
    'LOCAL_TAX_GENERAL'
  ))
);

-- Metadata only: no user question, answer, transcript, token, IP, device ID,
-- provider payload, or authentication secret.
CREATE TABLE app_private.interaction_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  intent app_private.intent_code NOT NULL,
  answer_status app_private.answer_status NOT NULL,
  fallback_reason app_private.fallback_reason,
  source_count integer NOT NULL DEFAULT 0 CHECK (source_count >= 0),
  used_source_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  response_time_ms integer NOT NULL CHECK (response_time_ms >= 0),
  selected_region text,
  routed_office_id uuid REFERENCES app_private.offices(id),
  is_test boolean NOT NULL DEFAULT false,
  request_id uuid NOT NULL UNIQUE,
  CHECK ((answer_status = 'FALLBACK') = (fallback_reason IS NOT NULL)),
  CHECK (answer_status <> 'SUCCESS' OR source_count > 0),
  CHECK (selected_region IS NULL OR selected_region IN (
    '아름동', '도담동', '조치원읍'
  ))
);

CREATE TABLE app_private.failed_questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  interaction_event_id uuid NOT NULL UNIQUE
    REFERENCES app_private.interaction_events(id) ON DELETE RESTRICT,
  masked_question text,
  intent app_private.intent_code NOT NULL,
  fallback_reason app_private.fallback_reason NOT NULL,
  candidate_eligible boolean NOT NULL,
  status app_private.candidate_status NOT NULL DEFAULT 'NEW',
  created_at timestamptz NOT NULL DEFAULT now(),
  text_expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days'),
  text_purged_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (intent IN (
    'MOVE_IN_RESIDENT_REGISTRATION',
    'CERTIFICATE_ISSUANCE',
    'BULKY_WASTE',
    'LOCAL_TAX_GENERAL'
  )),
  CHECK (candidate_eligible = (fallback_reason = 'INSUFFICIENT_GROUNDING')),
  CHECK (fallback_reason <> 'OUT_OF_SCOPE'),
  CHECK (status IN ('NEW', 'REASON_CONFIRMED')),
  CHECK (text_expires_at = created_at + interval '30 days'),
  CHECK (
    (masked_question IS NOT NULL AND text_purged_at IS NULL)
    OR (
      masked_question IS NULL
      AND text_purged_at IS NOT NULL
      AND text_purged_at >= text_expires_at
    )
  )
);

CREATE TABLE app_private.kb_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  failed_question_id uuid NOT NULL UNIQUE
    REFERENCES app_private.failed_questions(id) ON DELETE RESTRICT,
  title text NOT NULL,
  representative_question text NOT NULL,
  data_origin app_private.data_origin NOT NULL,
  category app_private.intent_code NOT NULL,
  answer_summary text NOT NULL,
  procedure_steps jsonb NOT NULL DEFAULT '[]'::jsonb,
  required_documents jsonb NOT NULL DEFAULT '[]'::jsonb,
  processing_time text,
  fee text,
  department text NOT NULL,
  source_title text NOT NULL,
  source_url text NOT NULL,
  last_verified_at date NOT NULL,
  caution text,
  created_by text NOT NULL,
  review_status app_private.candidate_status NOT NULL DEFAULT 'DRAFTED',
  reviewed_by text,
  review_comment text,
  approved_at timestamptz,
  activated_kb_id uuid UNIQUE REFERENCES app_private.kb_documents(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (category IN (
    'MOVE_IN_RESIDENT_REGISTRATION',
    'CERTIFICATE_ISSUANCE',
    'BULKY_WASTE',
    'LOCAL_TAX_GENERAL'
  )),
  CHECK (review_status IN (
    'DRAFTED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED'
  )),
  CHECK (reviewed_by IS NULL OR reviewed_by <> created_by),
  CHECK (review_comment IS NULL OR char_length(review_comment) <= 1000),
  CHECK (
    CASE review_status
      WHEN 'DRAFTED' THEN
        reviewed_by IS NULL AND review_comment IS NULL
        AND approved_at IS NULL AND activated_kb_id IS NULL
      WHEN 'PENDING_APPROVAL' THEN
        reviewed_by IS NULL AND review_comment IS NULL
        AND approved_at IS NULL AND activated_kb_id IS NULL
      WHEN 'APPROVED' THEN
        reviewed_by IS NOT NULL AND review_comment IS NOT NULL
        AND approved_at IS NOT NULL AND activated_kb_id IS NOT NULL
      WHEN 'REJECTED' THEN
        reviewed_by IS NOT NULL AND review_comment IS NOT NULL
        AND approved_at IS NULL AND activated_kb_id IS NULL
      ELSE false
    END
  )
);

-- Minimal append-only audit metadata only; never question/answer snapshots.
CREATE TABLE app_private.audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id text NOT NULL,
  actor_role app_private.admin_role NOT NULL,
  action text NOT NULL,
  target_type text NOT NULL,
  target_id uuid NOT NULL,
  old_status text,
  new_status text,
  changed_field_names jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_comment text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (action IN (
    'CANDIDATE_CREATED',
    'CANDIDATE_SUBMITTED',
    'CANDIDATE_APPROVED',
    'CANDIDATE_REJECTED',
    'FAILED_QUESTION_REASON_CONFIRMED'
  )),
  CHECK (target_type IN ('KB_CANDIDATE', 'FAILED_QUESTION')),
  CHECK (review_comment IS NULL OR char_length(review_comment) <= 1000)
);

-- Local/private durable retry metadata only. `20260722000660_chat_idempotency.sql`
-- is the executable authority for CHECKs, RLS, grants and capability functions.
-- No question text, masked question, correlation request ID, token, IP, device ID
-- or provider payload is projected or stored here.
CREATE TABLE app_private.chat_idempotency (
  idempotency_key uuid PRIMARY KEY,
  request_digest text NOT NULL,
  claim_token uuid,
  lease_expires_at timestamptz,
  state text NOT NULL,
  response_json jsonb,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  completed_at timestamptz,
  abandoned_at timestamptz,
  expires_at timestamptz NOT NULL
);

-- Local/private out-of-scope civic review queue. The executable authority is
-- `20260727000680_civic_scope_gap_queue.sql`; raw questions, answer/source
-- snapshots, context tokens, interaction/failed-question/candidate/KB links and
-- automatic activation are intentionally absent.
CREATE TABLE app_private.civic_scope_gaps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  masked_question text,
  status text NOT NULL DEFAULT 'NEW',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  text_expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days'),
  text_purged_at timestamptz,
  reviewed_by text,
  reviewed_at timestamptz,
  review_comment text
);

-- `00650` adds four backend-only local admin read capabilities:
-- app_api.list_failed_questions, app_api.get_failed_question,
-- app_api.list_kb_candidates and app_api.get_kb_candidate.
-- `00660` adds backend-only claim/complete/abandon/purge idempotency capabilities.
-- `00680` adds backend-only record/list/review/purge scope-gap capabilities.
-- Their SECURITY DEFINER, fixed search_path, revoke/grant posture and exact state
-- machine are intentionally not duplicated in this non-executable projection.

-- Final executable CHECK families (42) projected from migrations 00200+00400.
-- The migration helper implementations are intentionally not duplicated here.
--
-- kb_documents (7):
--   kb_documents_public_id_trimmed_nonempty_chk
--   kb_documents_required_text_trimmed_nonempty_chk
--   kb_documents_optional_text_trimmed_nonempty_chk
--   kb_documents_text_arrays_chk (non-empty strings only)
--   kb_documents_supported_category_chk
--   kb_documents_active_official_approval_chk
--   kb_documents_approver_not_author_chk
-- kb_question_examples (2):
--   kb_question_examples_question_trimmed_nonempty_chk
--   kb_question_examples_normalized_trimmed_nonempty_chk
-- offices (4):
--   offices_public_id_trimmed_nonempty_chk
--   offices_required_text_trimmed_nonempty_chk
--   offices_optional_text_trimmed_nonempty_chk
--   offices_supported_region_chk
-- office_service_mappings (2):
--   office_service_mappings_supported_intent_chk
--   office_service_mappings_department_trimmed_nonempty_chk
-- interaction_events (6):
--   interaction_events_status_reason_chk
--   interaction_events_used_sources_text_array_chk
--   interaction_events_used_sources_unique_chk
--   interaction_events_source_count_chk (array length equals source_count)
--   interaction_events_success_has_sources_chk
--   interaction_events_selected_region_chk
-- failed_questions (7):
--   failed_questions_masked_text_trimmed_nonempty_chk
--   failed_questions_supported_intent_chk
--   failed_questions_candidate_eligibility_chk
--   failed_questions_no_out_of_scope_chk
--   failed_questions_exact_expiry_chk
--   failed_questions_text_lifecycle_chk
--   failed_questions_status_subset_chk
-- kb_candidates (7; superseded approved-fields check is not part of the final set):
--   kb_candidates_required_text_trimmed_nonempty_chk
--   kb_candidates_optional_text_trimmed_nonempty_chk (review_comment <= 1000)
--   kb_candidates_text_arrays_chk (non-empty strings only)
--   kb_candidates_supported_category_chk
--   kb_candidates_reviewer_not_author_chk
--   kb_candidates_state_shape_chk
--   kb_candidates_status_subset_chk
-- audit_logs (7):
--   audit_logs_actor_trimmed_nonempty_chk
--   audit_logs_action_allowlist_chk (includes FAILED_QUESTION_REASON_CONFIRMED)
--   audit_logs_target_type_chk
--   audit_logs_status_values_chk
--   audit_logs_changed_fields_allowlist_chk
--   audit_logs_review_comment_trimmed_nonempty_chk (<= 1000)
--   audit_logs_action_shape_chk (exact actor/target/status/changed-fields shape)

CREATE INDEX idx_kb_active_official_category
  ON app_private.kb_documents (category)
  WHERE status = 'ACTIVE' AND data_origin = 'OFFICIAL';

CREATE INDEX idx_events_occurred
  ON app_private.interaction_events (occurred_at DESC);

CREATE INDEX idx_failures_status
  ON app_private.failed_questions (status, fallback_reason);

CREATE INDEX idx_failure_text_expiry
  ON app_private.failed_questions (text_expires_at)
  WHERE masked_question IS NOT NULL;

CREATE INDEX idx_candidates_status
  ON app_private.kb_candidates (review_status);

-- Executable migrations additionally enforce:
-- - trimmed/non-empty required and optional text fields;
-- - JSON arrays containing only unique, non-empty strings where required;
-- - source_count = length(used_source_ids) and source lineage to ACTIVE/OFFICIAL KB;
-- - immutable event/failure linkage and NEW -> REASON_CONFIRMED monotonicity;
-- - ACTIVE KB has at least one question example;
-- - exact audit action/actor/target/status/changed-field shapes;
-- - row locking, atomic candidate approval, append-only audit, RLS and ACLs.
-- - 00660 idempotency safe-response key denylist, independent claim-token ownership,
--   five-minute lease, exact 24-hour expiry and purge capability.
