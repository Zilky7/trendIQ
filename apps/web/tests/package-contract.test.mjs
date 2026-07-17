// @vitest-environment node
import { readFile } from "node:fs/promises";
import { expect, test } from "vitest";

test("web package declares dependencies required by its scripts", async () => {
  const packageText = await readFile(new URL("../package.json", import.meta.url));
  const packageJson = JSON.parse(packageText);
  const runtimeDependencies = packageJson.dependencies ?? {};
  const developmentDependencies = packageJson.devDependencies ?? {};

  for (const dependency of ["next", "react", "react-dom"]) {
    expect(runtimeDependencies[dependency], `missing runtime dependency: ${dependency}`).toBeTruthy();
  }

  for (const dependency of [
    "@playwright/test",
    "@types/node",
    "@types/react",
    "@types/react-dom",
    "typescript",
    "vitest",
  ]) {
    expect(
      developmentDependencies[dependency],
      `missing development dependency: ${dependency}`,
    ).toBeTruthy();
  }
});
