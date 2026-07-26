import assert from "node:assert/strict";
import test from "node:test";

import {
  extractOpenApiSchema,
  loadContracts,
} from "../src/contract-validator.mjs";

const { openApi } = loadContracts();

test("health and readiness 200 responses use strict required body components", () => {
  assert.equal(openApi.info.version, "3.2.0-draft");

  for (const [path, componentName, status] of [
    ["/health", "HealthResponse", "ok"],
    ["/ready", "ReadyResponse", "ready"],
  ]) {
    assert.deepEqual(
      openApi.paths[path].get.responses["200"].content["application/json"].schema,
      { $ref: `#/components/schemas/${componentName}` },
    );
    assert.deepEqual(openApi.components.schemas[componentName], {
      type: "object",
      additionalProperties: false,
      required: ["status"],
      properties: { status: { const: status } },
    });
  }
});

test("readiness and chat share the approved 503 response reference", () => {
  const expected = "#/components/responses/ServiceUnavailable";
  assert.equal(openApi.paths["/ready"].get.responses["503"].$ref, expected);
  assert.equal(
    openApi.paths["/api/v1/chat"].post.responses["503"].$ref,
    expected,
  );
});

test("chat idempotency key is an optional UUID distinct from request_id", () => {
  const parameter = openApi.components.parameters.IdempotencyKey;
  assert.equal(parameter.in, "header");
  assert.equal(parameter.name, "Idempotency-Key");
  assert.equal(parameter.required, false);
  assert.deepEqual(parameter.schema, { type: "string", format: "uuid" });
  assert.deepEqual(openApi.paths["/api/v1/chat"].post.parameters, [
    { $ref: "#/components/parameters/IdempotencyKey" },
  ]);
});

test("personal lookup and legal judgment expose UNKNOWN without becoming stored failures", () => {
  for (const schemaName of ["PersonalLookupResponse", "LegalJudgmentResponse"]) {
    assert.deepEqual(
      openApi.components.schemas[schemaName].allOf[1].properties.intent,
      { const: "UNKNOWN" },
    );
  }
});

test("503 Retry-After is an integer of at least one second", () => {
  const retryAfter =
    openApi.components.responses.ServiceUnavailable.headers["Retry-After"].schema;
  assert.deepEqual(retryAfter, { type: "integer", minimum: 1 });
});

test("HTTP 200 chat status excludes SYSTEM_ERROR", () => {
  const statuses = openApi.components.schemas.ChatAnswerStatus.enum;
  assert.deepEqual(statuses, ["SUCCESS", "FOLLOWUP", "FALLBACK"]);
  assert.ok(!statuses.includes("SYSTEM_ERROR"));
});

test("chat response is an explicit status-discriminated oneOf contract", () => {
  assert.deepEqual(openApi.components.schemas.ChatResponse.oneOf, [
    { $ref: "#/components/schemas/SuccessResponse" },
    { $ref: "#/components/schemas/FollowupResponse" },
    { $ref: "#/components/schemas/FallbackResponse" },
  ]);
  assert.ok(openApi.components.schemas.SuccessResponse.allOf[1].required.includes("office"));
  assert.ok(openApi.components.schemas.SuccessResponse.allOf[1].required.includes("answer_mode"));
  assert.deepEqual(openApi.components.schemas.SuccessResponse.allOf[1].properties.answer_mode, {
    enum: ["GENERATED", "TEMPLATE"],
  });
  assert.deepEqual(
    openApi.components.schemas.FollowupResponse.allOf[1].properties.office,
    { type: "null" },
  );
});

test("privacy unresolved stays public-only and storage reasons remain unchanged", () => {
  assert.deepEqual(openApi.components.schemas.FallbackReason.enum, [
    "INSUFFICIENT_GROUNDING",
    "PERSONAL_LOOKUP",
    "LEGAL_JUDGMENT",
    "OUT_OF_SCOPE",
    "PRIVACY_UNRESOLVED",
  ]);
  assert.deepEqual(openApi.components.schemas.StoredFailureReason.enum, [
    "INSUFFICIENT_GROUNDING",
    "PERSONAL_LOOKUP",
    "LEGAL_JUDGMENT",
  ]);
});

test("every approved admin success operation points to a typed envelope", () => {
  const expected = [
    ["/api/v1/admin/failed-questions", "get", "200", "FailedQuestionListResponse"],
    ["/api/v1/admin/failed-questions/{id}", "get", "200", "FailedQuestionDetailResponse"],
    ["/api/v1/admin/failed-questions/{id}/reason", "patch", "200", "ReasonConfirmationResponse"],
    ["/api/v1/admin/kb-candidates", "get", "200", "KBCandidateListResponse"],
    ["/api/v1/admin/kb-candidates", "post", "201", "KBCandidateCreateResponse"],
    ["/api/v1/admin/kb-candidates/{id}/submit", "post", "200", "KBCandidateSubmitResponse"],
    ["/api/v1/admin/kb-candidates/{id}/review", "patch", "200", "KBCandidateReviewResponse"],
  ];
  for (const [path, method, status, schema] of expected) {
    assert.deepEqual(
      openApi.paths[path][method].responses[status].content["application/json"].schema,
      { $ref: `#/components/schemas/${schema}` },
    );
  }
});

test("every declared admin 403, 404, 409, and 422 uses the closed admin error envelope", () => {
  const expected = { $ref: "#/components/responses/AdminError" };
  for (const [path, pathItem] of Object.entries(openApi.paths)) {
    if (!path.startsWith("/api/v1/admin/")) continue;
    for (const operation of Object.values(pathItem)) {
      if (!operation?.responses) continue;
      for (const status of ["403", "404", "409", "422"]) {
        if (operation.responses[status]) {
          assert.deepEqual(operation.responses[status], expected, `${path} ${status}`);
        }
      }
    }
  }
  assert.deepEqual(
    openApi.components.responses.AdminError.content["application/json"].schema,
    { $ref: "#/components/schemas/AdminErrorEnvelope" },
  );
});

test("admin filters, writes, and office queries use narrow request contracts", () => {
  assert.deepEqual(openApi.components.schemas.SupportedIntent.enum, [
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
  ]);
  assert.deepEqual(openApi.components.schemas.FailedQuestionStatus.enum, ["NEW", "REASON_CONFIRMED"]);
  assert.deepEqual(
    openApi.paths["/api/v1/offices"].get.parameters[1].schema,
    { $ref: "#/components/schemas/SupportedIntent" },
  );
  assert.deepEqual(
    openApi.paths["/api/v1/admin/failed-questions/{id}/reason"].patch.requestBody.content["application/json"].schema,
    { $ref: "#/components/schemas/ReasonConfirmationRequest" },
  );
  assert.deepEqual(
    openApi.paths["/api/v1/admin/kb-candidates/{id}/review"].patch.requestBody.content["application/json"].schema,
    { $ref: "#/components/schemas/CandidateReviewRequest" },
  );
});

test("OpenAPI extraction rejects external and unknown component references", () => {
  assert.throws(
    () =>
      extractOpenApiSchema(
        { components: { schemas: { Root: { $ref: "https://example.invalid/schema" } } } },
        "Root",
      ),
    /Unsupported OpenAPI schema reference/,
  );
  assert.throws(
    () =>
      extractOpenApiSchema(
        { components: { schemas: { Root: { $ref: "#\/components\/schemas\/Missing" } } } },
        "Root",
      ),
    /Unknown OpenAPI component schema/,
  );
});

test("OpenAPI extraction does not mutate its input", () => {
  const input = structuredClone(openApi);
  const before = structuredClone(input);
  extractOpenApiSchema(input, "ChatResponse");
  assert.deepEqual(input, before);
});
