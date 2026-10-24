import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

// Screen tests wait for data; on a busy machine or CI runner 1 s is too short.
import { configure } from "@testing-library/react";

configure({ asyncUtilTimeout: 5000 });
