BEGIN;

CREATE TABLE app_private.civic_scope_gaps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  masked_question text,
  status text NOT NULL DEFAULT 'NEW'
    CHECK (status IN ('NEW', 'PLANNED', 'DISMISSED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  text_expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days'),
  text_purged_at timestamptz,
  reviewed_by text,
  reviewed_at timestamptz,
  review_comment text,
  CHECK (text_expires_at = created_at + interval '30 days'),
  CHECK (
    (masked_question IS NOT NULL
      AND masked_question = pg_catalog.btrim(masked_question)
      AND pg_catalog.char_length(masked_question) BETWEEN 1 AND 2000
      AND text_purged_at IS NULL)
    OR (masked_question IS NULL AND text_purged_at IS NOT NULL)
  ),
  CHECK (
    (status = 'NEW'
      AND reviewed_by IS NULL
      AND reviewed_at IS NULL
      AND review_comment IS NULL)
    OR (status IN ('PLANNED', 'DISMISSED')
      AND reviewed_by IS NOT NULL
      AND reviewed_by = pg_catalog.btrim(reviewed_by)
      AND pg_catalog.char_length(reviewed_by) BETWEEN 1 AND 200
      AND reviewed_at IS NOT NULL
      AND review_comment IS NOT NULL
      AND review_comment = pg_catalog.btrim(review_comment)
      AND pg_catalog.char_length(review_comment) BETWEEN 1 AND 1000)
  )
);

ALTER TABLE app_private.civic_scope_gaps OWNER TO sejong_schema_owner;
ALTER TABLE app_private.civic_scope_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_private.civic_scope_gaps FORCE ROW LEVEL SECURITY;

CREATE POLICY civic_scope_gaps_owner_all ON app_private.civic_scope_gaps
  FOR ALL TO sejong_schema_owner USING (true) WITH CHECK (true);

CREATE TRIGGER trg_civic_scope_gaps_set_updated_at
BEFORE UPDATE ON app_private.civic_scope_gaps
FOR EACH ROW EXECUTE FUNCTION app_private.set_updated_at();

CREATE INDEX idx_civic_scope_gaps_status_created
  ON app_private.civic_scope_gaps (status, created_at DESC);

CREATE INDEX idx_civic_scope_gaps_text_expiry
  ON app_private.civic_scope_gaps (text_expires_at)
  WHERE masked_question IS NOT NULL;

CREATE FUNCTION app_api.record_civic_scope_gap(
  p_masked_question text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $record_civic_scope_gap$
DECLARE
  v_id uuid;
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_masked_question IS NULL
     OR p_masked_question IS DISTINCT FROM pg_catalog.btrim(p_masked_question)
     OR pg_catalog.char_length(p_masked_question) NOT BETWEEN 1 AND 2000 THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1010', MESSAGE = 'INVALID_CIVIC_SCOPE_GAP_TEXT';
  END IF;

  INSERT INTO app_private.civic_scope_gaps (
    masked_question, created_at, updated_at, text_expires_at
  ) VALUES (
    p_masked_question, v_now, v_now, v_now + interval '30 days'
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END
$record_civic_scope_gap$;

CREATE FUNCTION app_api.list_civic_scope_gaps(
  p_status text
)
RETURNS TABLE (
  id uuid,
  masked_question text,
  status text,
  created_at timestamptz,
  updated_at timestamptz,
  text_expires_at timestamptz,
  text_purged_at timestamptz,
  reviewed_by text,
  reviewed_at timestamptz,
  review_comment text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $list_civic_scope_gaps$
BEGIN
  IF p_status IS NOT NULL
     AND p_status NOT IN ('NEW', 'PLANNED', 'DISMISSED') THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1010', MESSAGE = 'INVALID_CIVIC_SCOPE_GAP_FILTER';
  END IF;

  RETURN QUERY
  SELECT
    gaps.id,
    gaps.masked_question,
    gaps.status,
    gaps.created_at,
    gaps.updated_at,
    gaps.text_expires_at,
    gaps.text_purged_at,
    gaps.reviewed_by,
    gaps.reviewed_at,
    gaps.review_comment
  FROM app_private.civic_scope_gaps AS gaps
  WHERE p_status IS NULL OR gaps.status = p_status
  ORDER BY gaps.created_at DESC, gaps.id;
END
$list_civic_scope_gaps$;

CREATE FUNCTION app_api.review_civic_scope_gap(
  p_scope_gap_id uuid,
  p_actor_id text,
  p_actor_role text,
  p_decision text,
  p_review_comment text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $review_civic_scope_gap$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_scope_gap_id IS NULL
     OR p_actor_id IS NULL
     OR p_actor_id IS DISTINCT FROM pg_catalog.btrim(p_actor_id)
     OR pg_catalog.char_length(p_actor_id) NOT BETWEEN 1 AND 200
     OR p_actor_role IS DISTINCT FROM 'APPROVER'
     OR p_decision IS NULL
     OR p_decision NOT IN ('PLANNED', 'DISMISSED')
     OR p_review_comment IS NULL
     OR p_review_comment IS DISTINCT FROM pg_catalog.btrim(p_review_comment)
     OR pg_catalog.char_length(p_review_comment) NOT BETWEEN 1 AND 1000 THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1010', MESSAGE = 'INVALID_CIVIC_SCOPE_GAP_REVIEW';
  END IF;

  UPDATE app_private.civic_scope_gaps AS gaps
  SET status = p_decision,
      reviewed_by = p_actor_id,
      reviewed_at = v_now,
      review_comment = p_review_comment
  WHERE gaps.id = p_scope_gap_id
    AND gaps.status = 'NEW';

  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1003', MESSAGE = 'INVALID_WORKFLOW_STATE';
  END IF;
END
$review_civic_scope_gap$;

CREATE FUNCTION app_api.purge_expired_civic_scope_gap_text()
RETURNS TABLE (
  purged_count integer,
  purged_ids uuid[]
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $purge_expired_civic_scope_gap_text$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  RETURN QUERY
  WITH purged AS (
    UPDATE app_private.civic_scope_gaps AS gaps
    SET masked_question = NULL,
        text_purged_at = v_now
    WHERE gaps.masked_question IS NOT NULL
      AND gaps.text_expires_at <= v_now
    RETURNING gaps.id
  )
  SELECT
    pg_catalog.count(*)::integer,
    COALESCE(
      pg_catalog.array_agg(purged.id ORDER BY purged.id),
      ARRAY[]::uuid[]
    )
  FROM purged;
END
$purge_expired_civic_scope_gap_text$;

ALTER FUNCTION app_api.record_civic_scope_gap(text)
  OWNER TO sejong_schema_owner;
ALTER FUNCTION app_api.list_civic_scope_gaps(text)
  OWNER TO sejong_schema_owner;
ALTER FUNCTION app_api.review_civic_scope_gap(uuid, text, text, text, text)
  OWNER TO sejong_schema_owner;
ALTER FUNCTION app_api.purge_expired_civic_scope_gap_text()
  OWNER TO sejong_schema_owner;

REVOKE ALL ON FUNCTION app_api.record_civic_scope_gap(text)
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.list_civic_scope_gaps(text)
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.review_civic_scope_gap(
  uuid, text, text, text, text
) FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.purge_expired_civic_scope_gap_text()
  FROM PUBLIC, anon, authenticated, sejong_backend;

GRANT EXECUTE ON FUNCTION app_api.record_civic_scope_gap(text)
  TO sejong_backend;
GRANT EXECUTE ON FUNCTION app_api.list_civic_scope_gaps(text)
  TO sejong_backend;
GRANT EXECUTE ON FUNCTION app_api.review_civic_scope_gap(
  uuid, text, text, text, text
) TO sejong_backend;
GRANT EXECUTE ON FUNCTION app_api.purge_expired_civic_scope_gap_text()
  TO sejong_backend;

COMMIT;
