import assert from "node:assert/strict";
import test from "node:test";

import {
  createContractValidators,
  readFixture,
} from "../src/contract-validator.mjs";

const validators = createContractValidators();

const requestCases = [
  ["valid-first-request.json", true],
  ["valid-null-context.json", true],
  ["invalid-session-id.json", false, { keyword: "additionalProperties", path: "", property: "session_id" }],
].map(([fixture, valid, error]) => ({
  contract: "OpenAPI ChatRequest",
  fixture: `chat-request/${fixture}`,
  validate: validators.request,
  valid,
  error,
}));

const responseExpectations = [
  ["valid-success.json", true],
  ["invalid-success-empty-sources.json", false, { keyword: "minItems", path: "/sources" }],
  ["valid-followup.json", true],
  ["valid-fallback-no-office.json", true],
  ["valid-fallback-office.json", true],
  ["valid-civic-scope-gap.json", true],
  ["valid-privacy-unresolved.json", true],
  ["invalid-privacy-copy.json", false],
  ["invalid-privacy-confidence.json", false, { keyword: "type", path: "/confidence" }],
  ["invalid-privacy-answer-payload.json", false, { keyword: "type", path: "/summary" }],
  ["invalid-privacy-candidate.json", false, { keyword: "const", path: "/fallback/candidate_eligible" }],
  ["invalid-privacy-office.json", false, { keyword: "type", path: "/fallback/office" }],
  ["invalid-success-fallback.json", false, { keyword: "type", path: "/fallback" }],
  ["invalid-followup-source.json", false, { keyword: "maxItems", path: "/sources" }],
  ["invalid-fallback-missing-fallback.json", false, { keyword: "required", path: "", property: "fallback" }],
  ["invalid-insufficient-candidate.json", false, { keyword: "const", path: "/fallback/candidate_eligible" }],
  ["invalid-out-of-scope-intent.json", false, { keyword: "const", path: "/intent" }],
  ["invalid-civic-scope-gap-intent.json", false, { keyword: "const", path: "/intent" }],
  ["invalid-fallback-context.json", false, { keyword: "type", path: "/context_token" }],
  ["invalid-missing-context.json", false, { keyword: "required", path: "", property: "context_token" }],
  ["invalid-session-id.json", false, { keyword: "unevaluatedProperties", path: "", property: "session_id" }],
  ["invalid-office-missing-id.json", false, { keyword: "required", path: "/fallback/office", property: "id" }],
  ["invalid-fallback-extra-property.json", false, { keyword: "unevaluatedProperties", path: "/fallback", property: "provider_debug" }],
];

const responseCases = responseExpectations.flatMap(([fixture, valid, error]) => [
  {
    contract: "OpenAPI ChatResponse",
    fixture: `chat-response/${fixture}`,
    validate: validators.openApiResponse,
    valid,
    error,
  },
  {
    contract: "standalone ChatResponse",
    fixture: `chat-response/${fixture}`,
    validate: validators.standaloneResponse,
    valid,
    error,
  },
]);

const errorCases = [
  ["valid-service-unavailable.json", true],
  ["invalid-code.json", false, { keyword: "const", path: "/error/code" }],
  ["invalid-extra-property.json", false, { keyword: "additionalProperties", path: "/error", property: "provider" }],
  ["invalid-request-id.json", false, { keyword: "required", path: "/error", property: "request_id" }],
].map(([fixture, valid, error]) => ({
  contract: "OpenAPI ServiceUnavailableEnvelope",
  fixture: `errors/${fixture}`,
  validate: validators.serviceUnavailable,
  valid,
  error,
}));

const adminCases = [
  ["valid-failed-question-list.json", "failedQuestionList", true],
  ["valid-failed-question-detail.json", "failedQuestionDetail", true],
  ["valid-reason-confirmation.json", "reasonConfirmation", true],
  ["valid-candidate-list.json", "candidateList", true],
  ["valid-candidate-create.json", "candidateCreate", true],
  ["valid-candidate-submit.json", "candidateSubmit", true],
  ["valid-candidate-review.json", "candidateReview", true],
  ["invalid-list-missing-total.json", "failedQuestionList", false, { keyword: "required", path: "", property: "total" }],
  ["invalid-review-status.json", "candidateReview", false, { keyword: "enum", path: "/status" }],
  ["valid-admin-error.json", "adminError", true],
  ["invalid-admin-error-echo.json", "adminError", false],
  ["invalid-admin-error-message.json", "adminError", false],
  ["invalid-failed-candidate-eligibility.json", "failedQuestionList", false],
  ["invalid-failed-null-without-purge.json", "failedQuestionDetail", false],
  ["invalid-failed-purge-before-expiry.json", "failedQuestionDetail", false],
  ["invalid-failed-text-with-purge.json", "failedQuestionDetail", false],
  ["invalid-failed-wrong-expiry.json", "failedQuestionDetail", false],
  ["invalid-candidate-approved-incomplete.json", "candidateList", false],
  ["invalid-candidate-self-review.json", "candidateList", false],
  ["invalid-candidate-pending-reviewed.json", "candidateList", false],
  ["invalid-candidate-rejected-activated.json", "candidateList", false],
  ["invalid-candidate-approved-mock.json", "candidateList", false],
].map(([fixture, validatorName, valid, error]) => ({
  contract: `OpenAPI ${validatorName}`,
  fixture: `admin/${fixture}`,
  validate: validators[validatorName],
  valid,
  error,
}));

const cases = [...requestCases, ...responseCases, ...errorCases, ...adminCases];
assert.equal(cases.length, 75, "fixture matrix must contain exactly 75 validations");

function summarizeErrors(errors = []) {
  return errors.map(({ instancePath, keyword, params }) => ({
    instancePath,
    keyword,
    property:
      params?.missingProperty ?? params?.additionalProperty ?? params?.unevaluatedProperty,
  }));
}

function hasExpectedError(errors, expected) {
  return errors.some(
    ({ instancePath, keyword, params }) =>
      keyword === expected.keyword &&
      instancePath === expected.path &&
      (expected.property === undefined ||
        params?.missingProperty === expected.property ||
        params?.additionalProperty === expected.property ||
        params?.unevaluatedProperty === expected.property),
  );
}

for (const fixtureCase of cases) {
  test(`${fixtureCase.contract}: ${fixtureCase.fixture}`, () => {
    const payload = readFixture(fixtureCase.fixture);
    if (!fixtureCase.fixture.startsWith("admin/")) {
      assert.match(
        JSON.stringify(payload),
        /(?:시연용 샘플|aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa)/,
        "contract fixtures must remain marked with a sample label or reserved UUID",
      );
    } else {
      assert.match(
        JSON.stringify(payload),
        /(?:10000000|20000000|30000000|synthetic|시연용 샘플)/,
        "admin fixtures must use reserved synthetic identities or explicit sample labels",
      );
    }
    const actual = fixtureCase.validate(payload);
    const errors = fixtureCase.validate.errors ?? [];

    assert.equal(
      actual,
      fixtureCase.valid,
      `unexpected validity: ${JSON.stringify(summarizeErrors(errors))}`,
    );
    if (!fixtureCase.valid) {
      if (fixtureCase.error) {
        assert.ok(
          hasExpectedError(errors, fixtureCase.error),
          `expected error semantics not found: ${JSON.stringify(summarizeErrors(errors))}`,
        );
      }
    }
  });
}
