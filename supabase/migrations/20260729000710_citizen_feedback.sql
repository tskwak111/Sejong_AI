BEGIN;

CREATE TABLE app_private.citizen_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  response_request_id uuid NOT NULL,
  rating text NOT NULL CHECK (rating IN ('SATISFIED', 'DISSATISFIED')),
  category text CHECK (
    category IS NULL OR category IN (
      'MOVE_IN_RESIDENT_REGISTRATION',
      'CERTIFICATE_ISSUANCE',
      'BULKY_WASTE',
      'LOCAL_TAX_GENERAL',
      'OTHER'
    )
  ),
  reason_code text CHECK (
    reason_code IS NULL OR reason_code IN (
      'INACCURATE',
      'NOT_RELEVANT',
      'HARD_TO_UNDERSTAND',
      'WRONG_CONTACT',
      'OTHER'
    )
  ),
  masked_detail text,
  detail_was_masked boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  detail_expires_at timestamptz,
  detail_purged_at timestamptz,
  UNIQUE (response_request_id),
  CHECK (
    (rating = 'SATISFIED'
      AND category IS NULL
      AND reason_code IS NULL
      AND masked_detail IS NULL
      AND detail_was_masked = false
      AND detail_expires_at IS NULL
      AND detail_purged_at IS NULL)
    OR
    (rating = 'DISSATISFIED'
      AND category IS NOT NULL
      AND reason_code IS NOT NULL
      AND (reason_code <> 'OTHER' OR masked_detail IS NOT NULL OR detail_purged_at IS NOT NULL)
      AND (detail_was_masked = false OR masked_detail IS NOT NULL OR detail_purged_at IS NOT NULL)
      AND (
        (masked_detail IS NULL AND detail_expires_at IS NULL AND detail_purged_at IS NULL)
        OR
        (masked_detail IS NOT NULL
          AND masked_detail = pg_catalog.btrim(masked_detail)
          AND pg_catalog.char_length(masked_detail) BETWEEN 1 AND 300
          AND detail_expires_at = created_at + interval '30 days'
          AND detail_purged_at IS NULL)
        OR
        (masked_detail IS NULL
          AND detail_expires_at = created_at + interval '30 days'
          AND detail_purged_at IS NOT NULL
          AND detail_purged_at >= detail_expires_at)
      ))
  )
);

ALTER TABLE app_private.citizen_feedback OWNER TO sejong_schema_owner;
ALTER TABLE app_private.citizen_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_private.citizen_feedback FORCE ROW LEVEL SECURITY;

CREATE POLICY citizen_feedback_owner_all ON app_private.citizen_feedback
  FOR ALL TO sejong_schema_owner USING (true) WITH CHECK (true);

CREATE INDEX idx_citizen_feedback_created
  ON app_private.citizen_feedback (created_at DESC, id);
CREATE INDEX idx_citizen_feedback_detail_expiry
  ON app_private.citizen_feedback (detail_expires_at)
  WHERE masked_detail IS NOT NULL;

CREATE FUNCTION app_api.record_citizen_feedback(
  p_response_request_id uuid,
  p_rating text,
  p_category text,
  p_reason_code text,
  p_masked_detail text,
  p_detail_was_masked boolean
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $record_citizen_feedback$
DECLARE
  v_id uuid;
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_response_request_id IS NULL
     OR p_rating IS NULL
     OR p_rating NOT IN ('SATISFIED', 'DISSATISFIED')
     OR p_detail_was_masked IS NULL
     OR (
       p_rating = 'SATISFIED'
       AND (
         p_category IS NOT NULL
         OR p_reason_code IS NOT NULL
         OR p_masked_detail IS NOT NULL
         OR p_detail_was_masked
       )
     )
     OR (
       p_rating = 'DISSATISFIED'
       AND (
         p_category IS NULL
         OR p_category NOT IN (
           'MOVE_IN_RESIDENT_REGISTRATION',
           'CERTIFICATE_ISSUANCE',
           'BULKY_WASTE',
           'LOCAL_TAX_GENERAL',
           'OTHER'
         )
         OR p_reason_code IS NULL
         OR p_reason_code NOT IN (
           'INACCURATE',
           'NOT_RELEVANT',
           'HARD_TO_UNDERSTAND',
           'WRONG_CONTACT',
           'OTHER'
         )
         OR (p_reason_code = 'OTHER' AND p_masked_detail IS NULL)
         OR (p_detail_was_masked AND p_masked_detail IS NULL)
       )
     )
     OR (
       p_masked_detail IS NOT NULL
       AND (
         p_masked_detail IS DISTINCT FROM pg_catalog.btrim(p_masked_detail)
         OR pg_catalog.char_length(p_masked_detail) NOT BETWEEN 1 AND 300
       )
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1010', MESSAGE = 'INVALID_CITIZEN_FEEDBACK';
  END IF;

  INSERT INTO app_private.citizen_feedback (
    response_request_id,
    rating,
    category,
    reason_code,
    masked_detail,
    detail_was_masked,
    created_at,
    detail_expires_at
  ) VALUES (
    p_response_request_id,
    p_rating,
    p_category,
    p_reason_code,
    p_masked_detail,
    p_detail_was_masked,
    v_now,
    CASE WHEN p_masked_detail IS NULL THEN NULL ELSE v_now + interval '30 days' END
  )
  ON CONFLICT (response_request_id) DO NOTHING
  RETURNING id INTO v_id;

  IF v_id IS NOT NULL THEN
    RETURN v_id;
  END IF;

  SELECT feedback.id
  INTO v_id
  FROM app_private.citizen_feedback AS feedback
  WHERE feedback.response_request_id = p_response_request_id
    AND feedback.rating = p_rating
    AND feedback.category IS NOT DISTINCT FROM p_category
    AND feedback.reason_code IS NOT DISTINCT FROM p_reason_code
    AND feedback.masked_detail IS NOT DISTINCT FROM p_masked_detail
    AND feedback.detail_was_masked = p_detail_was_masked;

  IF v_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1003', MESSAGE = 'FEEDBACK_REQUEST_CONFLICT';
  END IF;
  RETURN v_id;
END
$record_citizen_feedback$;

CREATE FUNCTION app_api.list_citizen_feedback(
  p_limit integer
)
RETURNS TABLE (
  id uuid,
  response_request_id uuid,
  rating text,
  category text,
  reason_code text,
  masked_detail text,
  detail_was_masked boolean,
  created_at timestamptz,
  detail_expires_at timestamptz,
  detail_purged_at timestamptz
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $list_citizen_feedback$
BEGIN
  IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100 THEN
    RAISE EXCEPTION USING
      ERRCODE = 'P1010', MESSAGE = 'INVALID_CITIZEN_FEEDBACK_LIMIT';
  END IF;

  RETURN QUERY
  SELECT
    feedback.id,
    feedback.response_request_id,
    feedback.rating,
    feedback.category,
    feedback.reason_code,
    feedback.masked_detail,
    feedback.detail_was_masked,
    feedback.created_at,
    feedback.detail_expires_at,
    feedback.detail_purged_at
  FROM app_private.citizen_feedback AS feedback
  ORDER BY feedback.created_at DESC, feedback.id
  LIMIT p_limit;
END
$list_citizen_feedback$;

CREATE FUNCTION app_api.summarize_citizen_feedback()
RETURNS TABLE (
  total_count integer,
  satisfied_count integer,
  dissatisfied_count integer,
  category_counts jsonb,
  reason_counts jsonb
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $summarize_citizen_feedback$
  SELECT
    (SELECT pg_catalog.count(*)::integer
     FROM app_private.citizen_feedback) AS total_count,
    (SELECT pg_catalog.count(*)::integer
     FROM app_private.citizen_feedback
     WHERE rating = 'SATISFIED') AS satisfied_count,
    (SELECT pg_catalog.count(*)::integer
     FROM app_private.citizen_feedback
     WHERE rating = 'DISSATISFIED') AS dissatisfied_count,
    COALESCE(
      (
        SELECT pg_catalog.jsonb_object_agg(counts.category, counts.count_value)
        FROM (
          SELECT category, pg_catalog.count(*)::integer AS count_value
          FROM app_private.citizen_feedback
          WHERE category IS NOT NULL
          GROUP BY category
        ) AS counts
      ),
      '{}'::jsonb
    ) AS category_counts,
    COALESCE(
      (
        SELECT pg_catalog.jsonb_object_agg(counts.reason_code, counts.count_value)
        FROM (
          SELECT reason_code, pg_catalog.count(*)::integer AS count_value
          FROM app_private.citizen_feedback
          WHERE reason_code IS NOT NULL
          GROUP BY reason_code
        ) AS counts
      ),
      '{}'::jsonb
    ) AS reason_counts
$summarize_citizen_feedback$;

CREATE FUNCTION app_api.purge_expired_citizen_feedback_detail()
RETURNS TABLE (
  purged_count integer,
  purged_ids uuid[]
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $purge_expired_citizen_feedback_detail$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  RETURN QUERY
  WITH purged AS (
    UPDATE app_private.citizen_feedback AS feedback
    SET masked_detail = NULL,
        detail_purged_at = v_now
    WHERE feedback.masked_detail IS NOT NULL
      AND feedback.detail_expires_at <= v_now
    RETURNING feedback.id
  )
  SELECT
    pg_catalog.count(*)::integer,
    COALESCE(
      pg_catalog.array_agg(purged.id ORDER BY purged.id),
      ARRAY[]::uuid[]
    )
  FROM purged;
END
$purge_expired_citizen_feedback_detail$;

ALTER FUNCTION app_api.record_citizen_feedback(uuid, text, text, text, text, boolean)
  OWNER TO sejong_schema_owner;
ALTER FUNCTION app_api.list_citizen_feedback(integer)
  OWNER TO sejong_schema_owner;
ALTER FUNCTION app_api.summarize_citizen_feedback()
  OWNER TO sejong_schema_owner;
ALTER FUNCTION app_api.purge_expired_citizen_feedback_detail()
  OWNER TO sejong_schema_owner;

REVOKE ALL ON FUNCTION app_api.record_citizen_feedback(
  uuid, text, text, text, text, boolean
) FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.list_citizen_feedback(integer)
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.summarize_citizen_feedback()
  FROM PUBLIC, anon, authenticated, sejong_backend;
REVOKE ALL ON FUNCTION app_api.purge_expired_citizen_feedback_detail()
  FROM PUBLIC, anon, authenticated, sejong_backend;

GRANT EXECUTE ON FUNCTION app_api.record_citizen_feedback(
  uuid, text, text, text, text, boolean
) TO sejong_backend;
GRANT EXECUTE ON FUNCTION app_api.list_citizen_feedback(integer)
  TO sejong_backend;
GRANT EXECUTE ON FUNCTION app_api.summarize_citizen_feedback()
  TO sejong_backend;
GRANT EXECUTE ON FUNCTION app_api.purge_expired_citizen_feedback_detail()
  TO sejong_backend;

COMMIT;
