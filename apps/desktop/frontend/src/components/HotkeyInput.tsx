import { Button } from "@heroui/react";
import { useEffect, useId, useRef, useState } from "react";
import type { Locale, Schema } from "../app/types";
import { hotkeyFromEvent, joinHotkey, splitHotkey } from "../utils/hotkeys";
import { DeckIcon } from "./DeckIcon";

export function HotkeyInput({ value, catalog, locale, platform, onChange }: { value: string; catalog: Schema["keys"]; locale: Locale; platform?: string; onChange: (value: string) => void }) {
  const [listOpen, setListOpen] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const captureRef = useRef<HTMLButtonElement>(null);
  const helpId = useId();
  const windows = platform === "win32" || platform === "windows";
  const parsed = splitHotkey(value, catalog);
  // The target host executes the shortcut; the browser's OS may be different.
  const modifierLabel = (modifier: Schema["keys"]["modifiers"][number]) =>
    modifier.name === "cmd" && windows
      ? "Win" : modifier[locale === "fr" ? "label_fr" : "label_en"];
  const label = [
    ...parsed.modifiers.map((name) => { const modifier = catalog.modifiers.find((item) => item.name === name); return modifier ? modifierLabel(modifier) : name; }),
    catalog.keys.find((item) => item.name === parsed.key)?.[locale === "fr" ? "label_fr" : "label_en"] ?? parsed.key.toUpperCase(),
  ].filter(Boolean).join(" + ");
  useEffect(() => {
    if (!capturing) return;
    const captureKey = (event: KeyboardEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const next = hotkeyFromEvent(event, catalog);
      if (!next) return;
      onChange(next);
      setCapturing(false);
    };
    const stopOutside = (event: PointerEvent) => {
      if (!captureRef.current?.contains(event.target as Node)) setCapturing(false);
    };
    window.addEventListener("keydown", captureKey, true);
    window.addEventListener("pointerdown", stopOutside, true);
    return () => {
      window.removeEventListener("keydown", captureKey, true);
      window.removeEventListener("pointerdown", stopOutside, true);
    };
  }, [capturing, catalog, onChange]);
  return <div className="hotkey-editor">
    <button ref={captureRef} className={`hotkey-capture ${capturing ? "capturing" : ""}`} type="button" aria-pressed={capturing} aria-describedby={windows ? helpId : undefined} onClick={() => { setListOpen(false); setCapturing(true); captureRef.current?.focus(); }}>
      <DeckIcon name={capturing ? "keyboard" : "star"} size={17} /><span>{capturing ? (locale === "fr" ? "Appuyez maintenant sur votre raccourci…" : "Press your shortcut now…") : label || (locale === "fr" ? "Cliquez puis appuyez sur les touches" : "Click, then press the keys")}</span>
    </button>
    <Button variant="ghost" size="sm" onPress={() => { setCapturing(false); setListOpen((open) => !open); }}>{locale === "fr" ? "Choisir" : "Choose"}</Button>
    {windows && <small id={helpId} className="hotkey-help">{locale === "fr" ? "Windows peut intercepter certains raccourcis Win. Utilisez « Choisir » pour les définir manuellement." : "Some Win shortcuts are handled by Windows before capture. Use Choose to set them manually."}</small>}
    {listOpen && <div className="hotkey-options">
      <div className="modifier-options">{catalog.modifiers.map((modifier) => { const active = parsed.modifiers.includes(modifier.name); return <button type="button" className={active ? "active" : ""} key={modifier.name} onClick={() => onChange(joinHotkey(active ? parsed.modifiers.filter((name) => name !== modifier.name) : [...parsed.modifiers, modifier.name], parsed.key, catalog))}>{modifierLabel(modifier)}</button>; })}</div>
      <select aria-label={locale === "fr" ? "Touche" : "Key"} value={parsed.key} onChange={(event) => onChange(joinHotkey(parsed.modifiers, event.target.value, catalog))}>
        <option value="">—</option>{catalog.keys.map((key) => <option key={key.name} value={key.name}>{key[locale === "fr" ? "label_fr" : "label_en"]}</option>)}
        <optgroup label="A–Z">{"abcdefghijklmnopqrstuvwxyz".split("").map((key) => <option key={key} value={key}>{key.toUpperCase()}</option>)}</optgroup>
        <optgroup label="0–9">{"0123456789".split("").map((key) => <option key={key} value={key}>{key}</option>)}</optgroup>
      </select>
    </div>}
  </div>;
}
