// @vitest-environment jsdom
import { test, expect } from "vitest";
test("S2-C1 clears the box", () => {
  expect(document.body.textContent).toContain("words: 0");
});
