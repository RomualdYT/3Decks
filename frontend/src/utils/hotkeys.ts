import type { Schema } from "../app/types";

export const CODE_TO_KEY = Object.freeze<Record<string, string>>({
  Escape: "escape", Enter: "return", NumpadEnter: "return", Tab: "tab", Space: "space",
  Backspace: "backspace", Delete: "forward_delete", ArrowLeft: "left", ArrowRight: "right",
  ArrowUp: "up", ArrowDown: "down", Home: "home", End: "end", PageUp: "pageup",
  PageDown: "pagedown", PrintScreen: "printscreen",
});

export function splitHotkey(value: string, catalog: Schema["keys"]) {
  const parts = value.split("+").map((part) => part.trim().toLowerCase()).filter(Boolean);
  const order = catalog.modifiers.map((modifier) => modifier.name);
  const known = new Set(order);
  return { modifiers: order.filter((name) => parts.includes(name)), key: parts.find((part) => !known.has(part)) ?? "" };
}

export function joinHotkey(modifiers: string[], key: string, catalog: Schema["keys"]): string {
  const selected = new Set(modifiers);
  return [...catalog.modifiers.map((modifier) => modifier.name).filter((name) => selected.has(name)), key].filter(Boolean).join("+");
}

export function hotkeyFromEvent(event: Pick<KeyboardEvent, "code" | "metaKey" | "ctrlKey" | "altKey" | "shiftKey">, catalog: Schema["keys"]): string {
  let key = CODE_TO_KEY[event.code] ?? "";
  if (!key && /^F([1-9]|1[0-2])$/.test(event.code)) key = event.code.toLowerCase();
  if (!key && /^Key[A-Z]$/.test(event.code)) key = event.code.slice(3).toLowerCase();
  if (!key && /^Digit[0-9]$/.test(event.code)) key = event.code.slice(5);
  if (!key) return "";
  const modifiers = [event.metaKey && "cmd", event.ctrlKey && "ctrl", event.altKey && "alt", event.shiftKey && "shift"].filter(Boolean) as string[];
  return joinHotkey(modifiers, key, catalog);
}
