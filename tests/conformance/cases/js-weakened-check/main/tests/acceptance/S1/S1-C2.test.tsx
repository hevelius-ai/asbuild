// @vitest-environment jsdom
import { test, expect } from "vitest";
import { render } from "@testing-library/react";
import { Counter } from "../../../src/Counter";
test("S1-C2 shows words: 0 for an empty box", () => {
  render(<Counter text="" />);
  expect(document.body.textContent).toContain("words: 0");
});
