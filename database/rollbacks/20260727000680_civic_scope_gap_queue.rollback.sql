BEGIN;

REVOKE ALL ON FUNCTION app_api.purge_expired_civic_scope_gap_text()
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.review_civic_scope_gap(
  uuid, text, text, text, text
) FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.list_civic_scope_gaps(text)
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.record_civic_scope_gap(text)
  FROM PUBLIC, anon, authenticated, sejong_backend;

DROP FUNCTION app_api.purge_expired_civic_scope_gap_text();
DROP FUNCTION app_api.review_civic_scope_gap(uuid, text, text, text, text);
DROP FUNCTION app_api.list_civic_scope_gaps(text);
DROP FUNCTION app_api.record_civic_scope_gap(text);
DROP TABLE app_private.civic_scope_gaps;

COMMIT;
