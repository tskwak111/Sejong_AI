BEGIN;

ALTER FUNCTION app_api.approve_kb_candidate(uuid, text, text, text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.confirm_failed_question_reason(uuid, text, text, text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.create_kb_candidate(
  uuid, text, text, text, text, text, text, jsonb, jsonb,
  text, text, text, text, text, date, text, text
)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.list_active_kb(text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.list_offices(text, text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.purge_expired_failed_question_text()
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.record_interaction(
  uuid, text, text, text, text[], integer, text, text, boolean, text
)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.reject_kb_candidate(uuid, text, text, text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_api.submit_kb_candidate(uuid, text, text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.is_allowed_audit_changed_fields(jsonb)
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.is_nonempty_text(text)
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.is_text_array(jsonb)
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.is_unique_text_array(jsonb)
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.lock_kb_question_parents()
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.purge_expired_failed_question_text_at(timestamp with time zone)
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.set_updated_at()
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.validate_active_kb_question()
  SET search_path = pg_catalog, pg_temp;
ALTER FUNCTION app_private.validate_failed_question_candidate()
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.validate_failed_question_event()
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.validate_interaction_event_failure()
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.validate_interaction_event_sources()
  SET search_path = pg_catalog;
ALTER FUNCTION app_private.validate_kb_candidate_failure()
  SET search_path = pg_catalog;

COMMIT;
