// @vitest-environment jsdom
import { test, expect } from "vitest";
import { render } from "@testing-library/react";
import { Counter } from "../../../src/Counter";
test("S1-C1 shows the word count", () => {
  render(<Counter text="a b c" />);
  expect(document.body.textContent).toContain("words: 3");
});
