import { describe, expect, it } from "vitest";

import { formatCount, formatPct, formatScore } from "@/lib/format";

describe("formatters", () => {
  it("formats rates, counts, and scores the way the screens read them", () => {
    expect(formatPct(0.0921)).toBe("9.21%");
    expect(formatCount(10000)).toBe("10,000");
    expect(formatScore(0.731)).toBe("0.73");
  });
});
