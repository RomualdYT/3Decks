import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { useDeckConfig } from "./useDeckConfig";
import { agentApi } from "../api/client";

vi.mock("../api/client", () => ({ agentApi: {
  schema: vi.fn(), config: vi.fn(), state: vi.fn(), apps: vi.fn(), save: vi.fn(),
} }));

let root: Root;
let container: HTMLDivElement;
let hook: ReturnType<typeof useDeckConfig>;
const documentAt = (revision: number) => ({ config: { revision, pages: [], features: { media: true } } });

function Harness() { hook = useDeckConfig(); return null; }

beforeEach(async () => {
  vi.useFakeTimers();
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  vi.mocked(agentApi.schema).mockResolvedValue({ features: [] } as never);
  vi.mocked(agentApi.config).mockResolvedValue(documentAt(1) as never);
  vi.mocked(agentApi.state).mockResolvedValue({ config_revision: 1 } as never);
  vi.mocked(agentApi.apps).mockResolvedValue({ apps: [] });
  container = document.createElement("div");
  root = createRoot(container);
  await act(async () => root.render(<Harness />));
});

afterEach(async () => {
  await act(async () => root.unmount());
  vi.restoreAllMocks();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("keeps an edit started while an external configuration is in flight", async () => {
  let resolve!: (value: never) => void;
  vi.mocked(agentApi.state).mockResolvedValue({ config_revision: 2 } as never);
  vi.mocked(agentApi.config).mockReturnValueOnce(new Promise(r => { resolve = r; }));
  await act(async () => vi.advanceTimersByTimeAsync(4000));
  await act(async () => hook.update(config => { config.features.media = false; }));
  await act(async () => resolve(documentAt(2) as never));
  expect(hook.config?.features.media).toBe(false);
  expect(hook.config?.revision).toBe(1);
  expect(hook.dirty).toBe(true);
});

it("does not overlap polling requests and accepts an external change when clean", async () => {
  let resolve!: (value: never) => void;
  vi.mocked(agentApi.state).mockResolvedValue({ config_revision: 2 } as never);
  vi.mocked(agentApi.config).mockReturnValueOnce(new Promise(r => { resolve = r; }));
  await act(async () => vi.advanceTimersByTimeAsync(12000));
  expect(agentApi.state).toHaveBeenCalledTimes(2); // initial load plus one poll
  await act(async () => resolve(documentAt(2) as never));
  expect(hook.config?.revision).toBe(2);
  expect(hook.dirty).toBe(false);
});

it("suspends polling in a hidden tab and refreshes on return", async () => {
  vi.spyOn(document, "hidden", "get").mockReturnValue(true);
  await act(async () => vi.advanceTimersByTimeAsync(16000));
  expect(agentApi.state).toHaveBeenCalledTimes(1);
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  await act(async () => document.dispatchEvent(new Event("visibilitychange")));
  expect(agentApi.state).toHaveBeenCalledTimes(2);
});
