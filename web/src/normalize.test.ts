import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { normalizeName } from "./normalize";

// Shared with scripts/build/tests/test_parse.py's
// test_normalize_name_matches_fixture_cases - both sides must agree
// exactly (see REFACTOR.md §8.2).
const fixturePath = fileURLToPath(
  new URL("../../scripts/build/tests/fixtures/normalize_cases.json", import.meta.url),
);
const cases: [string, string][] = JSON.parse(readFileSync(fixturePath, "utf-8"));

describe("normalizeName", () => {
  it("matches the shared Python/TypeScript fixture cases", () => {
    for (const [raw, expected] of cases) {
      expect(normalizeName(raw)).toBe(expected);
    }
  });
});
