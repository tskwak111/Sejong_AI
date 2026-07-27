import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const generatorUrl = new URL("../scripts/generate-api.mjs", import.meta.url);
const generatedUrl = new URL("../src/generated/api.ts", import.meta.url);
const rootPackageUrl = new URL("../../../package.json", import.meta.url);

test("the deterministic OpenAPI generator helper is present", () => {
  assert.ok(existsSync(generatorUrl), "scripts/generate-api.mjs is missing");
});

test("the generated TypeScript API source is tracked", () => {
  assert.ok(existsSync(generatedUrl), "src/generated/api.ts is missing");
});

test("root contract scripts call the deterministic helper without PATH pnpm", () => {
  const rootPackage = JSON.parse(readFileSync(rootPackageUrl, "utf8"));
  assert.equal(
    rootPackage.scripts["contracts:generate"],
    "node packages/shared-contracts/scripts/generate-api.mjs",
  );
  assert.equal(
    rootPackage.scripts["contracts:check"],
    "node packages/shared-contracts/scripts/generate-api.mjs --check",
  );
});

test("the tracked API source exactly matches a fresh render", async (t) => {
  if (!existsSync(generatorUrl) || !existsSync(generatedUrl)) {
    t.skip("generation helper and tracked source are required first");
    return;
  }

  const { renderGeneratedApi } = await import(generatorUrl.href);
  const tracked = readFileSync(generatedUrl, "utf8");
  assert.equal(await renderGeneratedApi(), tracked);
  assert.equal(await renderGeneratedApi(), tracked, "generation must be deterministic");

  const banner = tracked.split("\n").slice(0, 4).join("\n");
  assert.match(banner, /source: contracts\/openapi-v1\.yaml/);
  assert.match(banner, /OpenAPI: 4\.0\.0-draft/);
  assert.match(banner, /generator: openapi-typescript 7\.13\.0/);
  assert.doesNotMatch(banner, /\d{4}-\d{2}-\d{2}T|[A-Za-z]:\\/);
  assert.match(
    tracked,
    /simple_language\?: boolean;/,
    "an OpenAPI default must not make an optional request field required",
  );
  assert.match(tracked, /PRIVACY_UNRESOLVED/);
  assert.match(tracked, /CIVIC_SCOPE_GAP/);
  assert.match(tracked, /representative_question: string;/);
  assert.match(tracked, /data_origin: "OFFICIAL" \| "MOCK";/);
  for (const schemaName of [
    "FailedQuestionListResponse",
    "FailedQuestionDetailResponse",
    "ReasonConfirmationResponse",
    "KBCandidateListResponse",
    "KBCandidateCreateResponse",
    "KBCandidateSubmitResponse",
    "KBCandidateReviewResponse",
    "AdminErrorEnvelope",
    "SuccessResponse",
    "FollowupResponse",
    "FallbackResponse",
  ]) {
    assert.match(tracked, new RegExp(`${schemaName}:`));
  }
});
