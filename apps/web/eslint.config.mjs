import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypeScript,
  // design-ref는 디자인 시안 참고 자산(빌드·번들 미포함)이라 린트 제외
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "design-ref/**"]),
]);
