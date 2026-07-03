/**
 * Vitest setup: with `globals: false` (our config), @testing-library/react
 * does not register its automatic DOM cleanup, so renders would leak across
 * tests and getBy* queries start matching stale trees. Register it once here.
 */
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());
