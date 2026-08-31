import type { ActionSpec, ActionValue, ButtonConfig, DeckConfig, Locale, Localized, PageConfig } from "../app/types";

export const clone = <T,>(value: T): T => structuredClone(value);

export function localized(value: Localized | undefined, locale: Locale): string {
  if (typeof value === "string") return value;
  return value?.[locale] || value?.en || value?.fr || "";
}

export function setLocalized(value: Localized | undefined, locale: Locale, text: string): Localized {
  const next = typeof value === "string" ? { fr: value, en: value } : { ...value };
  next[locale] = text;
  return next.fr === next.en ? text : next;
}

export function actionKind(value: ActionValue): string {
  return typeof value === "string" ? value : value.type;
}

export function actionArgs(value: ActionValue): Record<string, unknown> {
  if (typeof value === "string") return {};
  const { type: _type, ...args } = value;
  return args;
}

export function defaultAction(spec: ActionSpec, config: DeckConfig, scenes: string[] = []): ActionValue {
  if (!spec.arguments.length) return spec.kind;
  const value: Record<string, unknown> = { type: spec.kind };
  for (const argument of spec.arguments) {
    if (argument.default !== undefined) value[argument.name] = argument.default;
    else if (argument.type === "boolean") value[argument.name] = false;
    else if (argument.type === "select") value[argument.name] = argument.choices?.[0]?.value ?? "";
    else if (argument.type === "number") value[argument.name] = spec.extension ? argument.min ?? 0 : 50;
    else if (argument.type === "page") value[argument.name] = config.pages[0]?.id ?? "";
    else if (argument.type === "script") value[argument.name] = Object.keys(config.scripts ?? {})[0] ?? "";
    else if (argument.name === "scene") value[argument.name] = scenes[0] ?? "";
    else value[argument.name] = "";
  }
  return value as ActionValue;
}

export function uniqueId(prefix: string, existing: string[]): string {
  let index = 1;
  while (existing.includes(`${prefix}${index}`)) index += 1;
  return `${prefix}${index}`;
}

export function newPage(config: DeckConfig): PageConfig {
  const id = uniqueId("page", config.pages.map((page) => page.id));
  return { id, title: { fr: "Nouvelle page", en: "New page" }, icon: "page", dashboard: "auto", layout: "grid", source: "", buttons: [] };
}

export function newButton(page: PageConfig, slot: number, spec: ActionSpec, config: DeckConfig, scenes: string[]): ButtonConfig {
  return {
    id: uniqueId("button", page.buttons.map((button) => button.id)),
    slot,
    label: { fr: spec.title.fr.slice(0, 24), en: spec.title.en.slice(0, 24) },
    icon: spec.icon,
    color: spec.color,
    action: defaultAction(spec, config, scenes),
  };
}
