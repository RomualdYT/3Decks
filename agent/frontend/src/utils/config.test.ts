import { describe, expect, it } from "vitest";
import type { ActionSpec, DeckConfig } from "../app/types";
import { actionArgs, actionKind, defaultAction, localized, newButton, newPage, reconcileCommittedConfig, setLocalized } from "./config";

const config: DeckConfig = {
  revision: 1,
  server: { host: "0.0.0.0", port: 38123, token: "", poll_interval: 1, volume_step: 5 },
  features: {}, integrations: { obs: { enabled: false, host: "127.0.0.1", port: 4455, password: "", timeout: 2 } },
  pages: [{ id: "main", title: "Main", icon: "star", dashboard: "auto", buttons: [] }],
};

const action: ActionSpec = {
  kind: "app.launch", category: "essential", icon: "app", color: "#4F8DF7",
  title: { fr: "Ouvrir", en: "Open" }, description: { fr: "Application", en: "Application" },
  arguments: [{ name: "target", type: "text", required: true }], supported: true, capability: "apps",
};

describe("configuration editor helpers", () => {
  it("keeps localized labels and falls back to English", () => {
    expect(localized({ en: "Main" }, "fr")).toBe("Main");
    const translated = setLocalized("Main", "fr", "Principal");
    expect(localized(translated, "fr")).toBe("Principal");
    expect(localized(translated, "en")).toBe("Main");
  });

  it("creates unique pages and buttons from the shared action schema", () => {
    const page = newPage(config);
    expect(page.id).toBe("page1");
    const button = newButton(config.pages[0], 2, action, config, []);
    expect(button.slot).toBe(2);
    expect(actionKind(button.action)).toBe("app.launch");
    expect(actionArgs(button.action)).toEqual({ target: "" });
  });

  it("pre-fills OBS scenes and page targets", () => {
    const obs = { ...action, kind: "obs.scene.set", arguments: [{ name: "scene", type: "text" as const, required: true }] };
    expect(actionArgs(defaultAction(obs, config, ["Camera"]))).toEqual({ scene: "Camera" });
  });

  it("preserves typed extension defaults and qualified action ids", () => {
    const extension: ActionSpec = { ...action, kind: "ext:com.example.timer/start", extension: "com.example.timer", arguments: [
      { name: "minutes", type: "number", required: true, min: 1, max: 180, default: 25 },
      { name: "silent", type: "boolean", required: false, default: false },
      { name: "mode", type: "select", required: false, choices: [{ value: "focus", label: "Focus" }] },
    ] };
    const value = defaultAction(extension, config);
    expect(actionKind(value)).toBe(extension.kind);
    expect(actionArgs(value)).toEqual({ minutes: 25, silent: false, mode: "focus" });
  });

  it("applies the committed document when no edit happened during save", () => {
    const submitted = structuredClone(config);
    const committed = { ...structuredClone(config), revision: 2 };
    expect(reconcileCommittedConfig(submitted, submitted, committed)).toEqual(committed);
  });

  it("keeps edits made while saving and advances only their revision", () => {
    const submitted = structuredClone(config);
    const current = structuredClone(config);
    current.pages[0].title = "Edited during save";
    const committed = { ...structuredClone(config), revision: 2 };

    const reconciled = reconcileCommittedConfig(current, submitted, committed);

    expect(reconciled.pages[0].title).toBe("Edited during save");
    expect(reconciled.revision).toBe(2);
    expect(current.revision).toBe(1);
  });
});
