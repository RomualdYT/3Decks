import type { CSSProperties } from "react";
import type { AgentState, DeckConfig, Locale, PageConfig } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { localized } from "../utils/config";
import { DeckIcon } from "../components/DeckIcon";
import { extensionSource } from "../extensions/ExtensionPreview";

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
  return (
    <div className="preview-column">
      <div className="workspace-heading">
        <div><span className="eyebrow">{t("page")} {pageIndex + 1}</span><h1>{localized(page.title, locale) || page.id}</h1></div>
      </div>
      <div className="device-stage">
        <div className="device-shell-wrap">
          <img className="device-shell-image" src="/device-shell.png" alt="" draggable={false} />
          <ConsoleTopScreen page={page} status={status} locale={locale} />
          <section className="device-bottom-screen" aria-label={fr ? "Aperçu de l’écran tactile" : "Touch screen preview"}>
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
                <div className="console-grid">
                  {Array.from({ length: slots }, (_, slot) => {
                    const button = previewButtons.find((item) => item.slot === slot);
                    const dynamicLabel = dynamic && button ? localized(button.label, locale) : "";
                    return (
                      <button
                        key={slot}
                        type="button"
                        disabled={dynamic && !button}
                        className={`${button ? "configured" : "empty"} ${selectedSlot === slot ? "selected" : ""} ${dynamicLabel ? "dynamic" : ""}`}
                        style={button ? { "--button-color": button.color } as CSSProperties : undefined}
                        draggable={Boolean(button) && !dynamic}
                        onDragStart={(event) => event.dataTransfer.setData("text/deck-slot", String(slot))}
                        onDragOver={(event) => { if (event.dataTransfer.types.includes("text/deck-slot")) event.preventDefault(); }}
                        onDrop={(event) => { event.preventDefault(); if (!dynamic) onMoveButton(Number(event.dataTransfer.getData("text/deck-slot")), slot); }}
                        onClick={() => onSelectSlot(slot)}
                      >
                        {(button || !dynamic) && <span className="console-button-icon"><DeckIcon name={button?.icon ?? "plus"} size={20} /></span>}
                        <strong>{button ? localized(button.label, locale) : dynamic ? "" : t("emptySlot")}</strong>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
            <nav className="console-page-nav" aria-label={fr ? "Pages de la console" : "Console pages"}>
              {config.pages.map((item, index) => <button key={item.id} type="button" aria-label={localized(item.title, locale) || item.id} className={index === pageIndex ? "active" : ""} onClick={() => onSelectPage(index)}><DeckIcon name={item.icon || "page"} size={12} /><span>{localized(item.title, locale) || item.id}</span></button>)}
            </nav>
          </section>
        </div>
      </div>
      <p className="preview-caption"><DeckIcon name="info" size={16} />{dynamic ? (fr ? "Contenu automatique : l’intégration choisit les boutons et leur ordre." : "Automatic content: the integration chooses the buttons and their order.") : (fr ? "Aperçu fidèle de vos deux écrans. Glissez les actions pour les réorganiser." : "Accurate preview of both screens. Drag actions to reorder them.")}</p>
    </div>
  );
}
