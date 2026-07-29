BEGIN;

REVOKE ALL ON FUNCTION app_api.purge_expired_citizen_feedback_detail()
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.list_citizen_feedback(integer)
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.summarize_citizen_feedback()
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.record_citizen_feedback(
  uuid, text, text, text, text, boolean
) FROM PUBLIC, anon, authenticated, sejong_backend;

DROP FUNCTION app_api.purge_expired_citizen_feedback_detail();
DROP FUNCTION app_api.summarize_citizen_feedback();
DROP FUNCTION app_api.list_citizen_feedback(integer);
DROP FUNCTION app_api.record_citizen_feedback(uuid, text, text, text, text, boolean);
DROP TABLE app_private.citizen_feedback;

COMMIT;
