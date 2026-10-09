import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import catalog from "../../../catalog.json";
import type { Locale } from "../app/types";
import { HotkeyInput } from "./HotkeyInput";

let root: Root, container: HTMLDivElement;
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

it.each(["en", "fr"] as const)("labels an existing Cmd shortcut as Win on the Windows host (%s)", async (locale) => {
  await act(async () => root.render(<HotkeyInput value="cmd+d" catalog={catalog.keys} locale={locale} platform="win32" onChange={vi.fn()} />));
  expect(container.querySelector(".hotkey-capture")?.textContent).toBe("Win + D");
});

it.each(["darwin", "macos", undefined])("preserves the catalog's Cmd label on host %s", async (platform) => {
  await act(async () => root.render(<HotkeyInput value="cmd+d" catalog={catalog.keys} locale="en" platform={platform} onChange={vi.fn()} />));
  expect(container.querySelector(".hotkey-capture")?.textContent).toBe("Cmd + D");
  expect(container.querySelector(".hotkey-help")).toBeNull();
});

it.each(["en", "fr"] as const)("explains the manual fallback for Windows-reserved shortcuts (%s)", async (locale) => {
  await act(async () => root.render(<HotkeyInput value="" catalog={catalog.keys} locale={locale} platform="win32" onChange={vi.fn()} />));
  expect(container.textContent).toContain(locale === "fr" ? "Utilisez « Choisir »" : "Use Choose to set them manually");
  const help = container.querySelector(".hotkey-help")!;
  expect(container.querySelector(".hotkey-capture")?.getAttribute("aria-describedby")).toBe(help.id);
});

async function mountEditor(locale: Locale, onChange = vi.fn(), initial = "d") {
  function Editor() {
    const [value, setValue] = useState(initial);
    return <HotkeyInput value={value} catalog={catalog.keys} locale={locale} platform="win32" onChange={(next) => { setValue(next); onChange(next); }} />;
  }
  await act(async () => root.render(<Editor />));
  return onChange;
}

it.each(["en", "fr"] as const)("manually selects Win without changing the stored shortcut grammar (%s)", async (locale) => {
  const onChange = await mountEditor(locale);
  const choose = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === (locale === "fr" ? "Choisir" : "Choose"))!;
  await act(async () => choose.click());
  const win = Array.from(container.querySelectorAll(".modifier-options button")).find((button) => button.textContent === "Win") as HTMLButtonElement;
  expect(win).toBeDefined();
  await act(async () => win.click());
  expect(onChange).toHaveBeenLastCalledWith("cmd+d");
  expect(container.querySelector(".hotkey-capture")?.textContent).toBe("Win + D");
  expect(win.classList.contains("active")).toBe(true);
  await act(async () => win.click());
  expect(onChange).toHaveBeenLastCalledWith("d");
});

it("captures a delivered Meta chord but waits for a main key", async () => {
  const onChange = await mountEditor("en");
  await act(async () => (container.querySelector(".hotkey-capture") as HTMLButtonElement).click());
  await act(async () => window.dispatchEvent(new KeyboardEvent("keydown", { code: "MetaLeft", metaKey: true, bubbles: true, cancelable: true })));
  expect(onChange).not.toHaveBeenCalled();
  expect(container.querySelector(".hotkey-capture")?.getAttribute("aria-pressed")).toBe("true");
  await act(async () => window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyD", metaKey: true, bubbles: true, cancelable: true })));
  expect(onChange).toHaveBeenLastCalledWith("cmd+d");
  expect(container.querySelector(".hotkey-capture")?.textContent).toBe("Win + D");
  expect(container.querySelector(".hotkey-capture")?.getAttribute("aria-pressed")).toBe("false");
});

it("edits a win alias without dropping the main key", async () => {
  const onChange = await mountEditor("en", vi.fn(), "win+d");
  expect(container.querySelector(".hotkey-capture")?.textContent).toBe("Win + D");
  const choose = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Choose")!;
  await act(async () => choose.click());
  const shift = Array.from(container.querySelectorAll(".modifier-options button")).find((button) => button.textContent === "Shift") as HTMLButtonElement;
  await act(async () => shift.click());
  expect(onChange).toHaveBeenLastCalledWith("cmd+shift+d");
});
