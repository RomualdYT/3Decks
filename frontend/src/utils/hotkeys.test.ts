import { describe, expect, it } from "vitest";
import type { Schema } from "../app/types";
import { hotkeyFromEvent, joinHotkey, splitHotkey } from "./hotkeys";

const catalog: Schema["keys"] = {
  modifiers: [
    { name: "cmd", label_en: "Cmd", label_fr: "Cmd" },
    { name: "ctrl", label_en: "Ctrl", label_fr: "Ctrl" },
    { name: "alt", label_en: "Alt", label_fr: "Alt" },
    { name: "shift", label_en: "Shift", label_fr: "Maj" },
  ],
  groups: ["editing", "navigation", "function"],
  keys: [{ name: "escape", label_en: "Escape", label_fr: "Échap", group: "editing" }],
};

describe("hotkey editor", () => {
  it("normalizes modifiers in catalog order", () => {
    expect(joinHotkey(["shift", "cmd"], "a", catalog)).toBe("cmd+shift+a");
    expect(splitHotkey("shift+cmd+a", catalog)).toEqual({ modifiers: ["cmd", "shift"], key: "a" });
  });

  it("captures physical keys independently from keyboard labels", () => {
    expect(hotkeyFromEvent({ code: "KeyQ", metaKey: true, ctrlKey: false, altKey: false, shiftKey: true }, catalog)).toBe("cmd+shift+q");
    expect(hotkeyFromEvent({ code: "Escape", metaKey: false, ctrlKey: false, altKey: false, shiftKey: false }, catalog)).toBe("escape");
  });
});
