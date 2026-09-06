import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ConsoleTopScreen, dashboardMode, mediaTime } from "./ConsoleTopScreen";
import { agentApi } from "../api/client";
import type { AgentState, PageConfig } from "../app/types";

vi.mock("../api/client", () => ({ agentApi: { artwork: vi.fn() } }));
let root: Root, container: HTMLDivElement;
const page: PageConfig = { id: "main", title: "Main", icon: "star", dashboard: "auto", buttons: [] };
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:test-cover"), revokeObjectURL: vi.fn() });
  vi.mocked(agentApi.artwork).mockResolvedValue(new Blob(["image"], { type: "image/png" }));
  container = document.createElement("div");
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); vi.clearAllMocks(); vi.unstubAllGlobals(); });

it("uses the console automatic mode and formats seconds without jumps", () => {
  expect(dashboardMode(page, {})).toBe("apps");
  expect(dashboardMode(page, { title: "Song" })).toBe("media");
  expect(mediaTime(65.9)).toBe("1:05");
  expect(mediaTime(null)).toBe("0:00");
});

it("renders real media metadata, artwork and duration; disposes the image on mode change", async () => {
  const status = { clients: [{}], snapshot: { time: "12:34", media: {
    title: "Example song", artist: "Example artist", album: "Album", app: "Spotify",
    position: 65, duration: 285, art: 123, playing: true,
  } } } as unknown as AgentState;
  await act(async () => root.render(<ConsoleTopScreen page={page} status={status} locale="en" />));
  expect(container.textContent).toContain("Example song");
  expect(container.textContent).toContain("Album");
  expect(container.textContent).toContain("1:05");
  expect(container.textContent).toContain("4:45");
  expect(container.querySelector("image")?.getAttribute("href")).toBe("blob:test-cover");
  expect(container.querySelectorAll(".console-equalizer rect")).toHaveLength(16);
  await act(async () => root.render(<ConsoleTopScreen page={{ ...page, dashboard: "audio" }} status={status} locale="fr" />));
  expect(container.textContent).toContain("SORTIE AUDIO");
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test-cover");
  // Returning before the next download finishes must not reference a revoked URL.
  vi.mocked(agentApi.artwork).mockReturnValueOnce(new Promise(() => {}));
  await act(async () => root.render(<ConsoleTopScreen page={page} status={status} locale="en" />));
  expect(container.querySelector("image")).toBeNull();
});

it("does not invent metrics or keep media on an empty frame page", async () => {
  await act(async () => root.render(<ConsoleTopScreen page={{ ...page, dashboard: "system" }} status={null} locale="en" />));
  expect(container.textContent).toContain("Waiting for metrics");
  expect(container.textContent).not.toContain("0%");
  await act(async () => root.render(<ConsoleTopScreen page={{ ...page, dashboard: "frame" }} status={null} locale="en" />));
  expect(container.textContent).toContain("Nothing playing");
  expect(agentApi.artwork).not.toHaveBeenCalled();
});
