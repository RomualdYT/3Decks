import type { CSSProperties } from "react";
import type { AgentState, DeckConfig, Locale, PageConfig } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { localized } from "../utils/config";
import { DeckIcon } from "../components/DeckIcon";
import { extensionSource } from "../extensions/ExtensionPreview";

import { ConsoleTouchCanvas } from "./ConsoleTouchCanvas";
import { deviceShellStyle } from "./deviceShell";
import { ConsoleTopScreen } from "./ConsoleTopScreen";

interface Props {
  config: DeckConfig;
  page: PageConfig;
  pageIndex: number;
  locale: Locale;
  selectedSlot: number | null;
  status: AgentState | null;
  slots: number;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onSelectPage: (index: number) => void;
  onSelectSlot: (slot: number) => void;
  onMoveButton: (from: number, to: number) => void;
}

export function DeckPreview({ config, page, pageIndex, locale, selectedSlot, status, slots, t, onSelectPage, onSelectSlot, onMoveButton }: Props) {
  const dynamic = Boolean(page.source);
  const customSource = page.source?.startsWith("ext:");
  const fr = locale === "fr";
  const appItems = Array.isArray(status?.snapshot?.apps) ? status.snapshot.apps.map(String) : [];
  const generated = customSource ? extensionSource(status, page.source!) : appItems.map((label) => ({ id: label, label, detail: "", icon: "app", color: "#66CB10", active: false }));
  const previewButtons = dynamic ? generated.map((entry, slot) => ({ ...entry, slot, action: "noop" })) : page.buttons;
  const pageCount = Math.max(1, config.pages.length);
  const inactiveTabWidth = pageCount <= 6 ? 30 : (260 - (pageCount - 1) * 3) / pageCount;
  const activeTabWidth = pageCount <= 6 ? Math.min(88, 260 - (inactiveTabWidth + 3) * (pageCount - 1)) : inactiveTabWidth;
  const pageAccent = typeof page.accent === "string" && page.accent ? page.accent : "#66cb10";
  const snapshot = status?.snapshot ?? {};
  const media = (snapshot.media ?? {}) as Record<string, unknown>;
  const activeButton = (button: PageConfig["buttons"][number]) => {
    if ("active" in button) return button.active === true;
    if (button.toggle === "playing") return media.playing === true;
    if (button.toggle === "media_present") return Boolean(media.title);
    if (button.toggle === "muted" || button.toggle === "mic_muted") return snapshot[button.toggle] === true;
    return false;
  };
  return (
    <div className="preview-column">
      <div className="device-stage">
        <div className="device-shell-wrap" style={deviceShellStyle}>
          <img className="device-shell-image" src="/device-shell.svg" alt="" draggable={false} />
          <ConsoleTopScreen page={page} status={status} locale={locale} />
          <section className="device-bottom-screen" aria-label={fr ? "Aperçu de l’écran tactile" : "Touch screen preview"}>
            <ConsoleTouchCanvas style={{ "--page-accent": pageAccent } as CSSProperties}>
            <header className="console-touch-header">
              <strong>{localized(page.title, locale) || page.id}</strong>
              {config.pages.length > 1 && <span className="console-page-dots" aria-hidden="true">{config.pages.map((item, index) => <i key={item.id} className={index === pageIndex ? "active" : ""} />)}</span>}
            </header>
            {page.dashboard === "lyrics" && media.seekable === true && Number(media.duration) > 0 && <div className="console-seek-preview"><i style={{ width: `${Math.min(100, Math.max(0, Number(media.position || 0) / Number(media.duration) * 100))}%` }} /></div>}
            <div className={`screen-content ${page.layout === "list" ? "list-mode" : "grid-mode"}`}>
              {dynamic && !generated.length ? <div className="dynamic-empty"><span><DeckIcon name={customSource ? "extension" : "app"} size={25} /></span><strong>{customSource ? (fr ? "Contenu d’extension" : "Extension content") : (fr ? "Fenêtres disponibles" : "Available windows")}</strong><p>{customSource ? (fr ? "Cette zone affichera les éléments fournis par l’extension. Vérifiez son activation dans Extensions." : "Items provided by the extension appear here. Check its status in Extensions.") : (fr ? "Cette zone se remplira automatiquement avec les applications ouvertes sur votre ordinateur." : "This area fills automatically with apps open on your computer.")}</p></div> : null}
              {page.layout === "list" ? (
                <div className="console-list">
                  {previewButtons.slice(0, dynamic ? 32 : slots).map((item) => {
                    const button = typeof item === "object" && item && "slot" in item ? item as PageConfig["buttons"][number] : null;
                    const label = button ? localized(button.label, locale) : String(item);
                    return <button key={button?.id ?? label} type="button" onClick={() => !dynamic && button && onSelectSlot(button.slot)}><span><DeckIcon name={button?.icon ?? "app"} size={16} /></span><strong>{label}</strong><small>›</small></button>;
                  })}
                  {!dynamic && !page.buttons.length && <button type="button" className="list-empty" onClick={() => onSelectSlot(0)}><DeckIcon name="plus" size={16} />{t("addAction")}</button>}
                </div>
              ) : !dynamic || generated.length ? (
                <div className="console-grid" key={page.id}>
                  {Array.from({ length: slots }, (_, slot) => {
                    const button = previewButtons.find((item) => item.slot === slot);
                    const active = button ? activeButton(button) : false;
                    const icon = active && button?.icon === "play" ? "pause" : active && button?.icon === "mic" ? "mic-off" : button?.icon;
                    const dynamicLabel = dynamic && button ? localized(button.label, locale) : "";
                    return (
                      <button
                        key={slot}
                        type="button"
                        disabled={dynamic && !button}
                        className={`${button ? "configured" : "empty"} ${selectedSlot === slot ? "selected" : ""} ${dynamicLabel ? "dynamic" : ""} ${active ? "is-active" : ""}`}
                        style={{ "--button-color": button?.color } as CSSProperties}
                        draggable={Boolean(button) && !dynamic}
                        onDragStart={(event) => event.dataTransfer.setData("text/deck-slot", String(slot))}
                        onDragOver={(event) => { if (event.dataTransfer.types.includes("text/deck-slot")) event.preventDefault(); }}
                        onDrop={(event) => { event.preventDefault(); if (!dynamic) onMoveButton(Number(event.dataTransfer.getData("text/deck-slot")), slot); }}
                        onClick={() => onSelectSlot(slot)}
                      >
                        {(button || !dynamic) && <span className="console-button-icon"><DeckIcon name={icon ?? "plus"} size={28} /></span>}
                        {button && "hold_label" in button && button.hold_label && <span className="console-hold-marker" aria-hidden="true">···</span>}
                        {active && <i className="console-active-marker" aria-hidden="true" />}
                        <strong>{button ? localized(button.label, locale) : dynamic ? "" : t("emptySlot")}</strong>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
            <nav className="console-page-nav" aria-label={fr ? "Pages de la console" : "Console pages"}>
              <div className="console-page-tabs" style={{ "--dock-width": `${activeTabWidth + (inactiveTabWidth + 3) * (pageCount - 1) + 6}px` } as CSSProperties}>
              {config.pages.map((item, index) => <button key={item.id} type="button" aria-label={localized(item.title, locale) || item.id} title={localized(item.title, locale) || item.id} className={index === pageIndex ? "active" : ""} style={{ width: index === pageIndex ? activeTabWidth : inactiveTabWidth, "--tab-accent": typeof item.accent === "string" && item.accent ? item.accent : "#66cb10" } as CSSProperties} onClick={() => onSelectPage(index)}><DeckIcon name={item.icon || "page"} size={inactiveTabWidth < 24 ? inactiveTabWidth * .72 : index === pageIndex && activeTabWidth >= 64 ? 15 : 17} />{index === pageIndex && activeTabWidth >= 64 && <span>{localized(item.title, locale) || item.id}</span>}</button>)}
              </div>
              <span className="console-settings-icon" role="img" aria-label={fr ? "Réglages sur la console" : "Settings on the console"}><DeckIcon name="gear" size={16} /></span>
            </nav>
            </ConsoleTouchCanvas>
          </section>
        </div>
      </div>
      <p className="preview-caption"><DeckIcon name="info" size={16} />{dynamic ? (fr ? "Contenu automatique : l’intégration choisit les boutons et leur ordre." : "Automatic content: the integration chooses the buttons and their order.") : (fr ? "Aperçu fidèle de vos deux écrans. Glissez les actions pour les réorganiser." : "Accurate preview of both screens. Drag actions to reorder them.")}</p>
    </div>
  );
}
