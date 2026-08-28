import type { CSSProperties } from "react";
import type { AgentState, DeckConfig, Locale, PageConfig } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { localized } from "../utils/config";
import { DeckIcon } from "../components/DeckIcon";

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

function mediaData(status: AgentState | null) {
  const value = status?.snapshot?.media;
  return value && typeof value === "object" ? value as Record<string, unknown> : null;
}

function TopScreen({ page, status, locale }: Pick<Props, "page" | "status" | "locale">) {
  const fr = locale === "fr";
  const media = mediaData(status);
  const cpu = status?.snapshot?.cpu;
  const memory = status?.snapshot?.memory;
  const notifications = Array.isArray(status?.snapshot?.notifications) ? status.snapshot.notifications as Array<Record<string, unknown>> : [];
  const mode = page.dashboard === "auto" ? (media?.title ? "media" : "system") : page.dashboard;
  return (
    <section className="device-top-screen" aria-label={fr ? "Aperçu de l’écran supérieur" : "Top screen preview"}>
      <header><span>3DECKS</span><span><i className={status?.clients.length ? "online" : ""} />{status?.clients.length ? (fr ? "CONNECTÉ" : "CONNECTED") : (fr ? "APERÇU" : "PREVIEW")}</span></header>
      {mode === "media" && <div className="top-media"><div className="top-art"><DeckIcon name="music" size={35} /></div><div><small>{String(media?.app ?? "APPLE MUSIC · SPOTIFY")}</small><strong>{String(media?.title ?? (fr ? "Aucune lecture" : "Nothing playing"))}</strong><span>{String(media?.artist ?? (fr ? "Le média en cours apparaîtra ici" : "Current media will appear here"))}</span><div className="top-progress"><i /></div></div></div>}
      {mode === "notifications" && <div className="top-dashboard-list"><div className="top-title"><DeckIcon name="bell" size={16} /><strong>{fr ? "Notifications" : "Notifications"}</strong><small>{notifications.length}</small></div>{notifications.length ? notifications.slice(0, 2).map((item, index) => <div className="top-list-row" key={index}><span><DeckIcon name="bell" size={14} /></span><div><strong>{String(item.title ?? item.app ?? "Notification")}</strong><small>{String(item.body ?? item.app ?? "")}</small></div></div>) : <div className="top-empty"><DeckIcon name="bell" size={24} /><span>{fr ? "Les notifications récentes apparaîtront ici" : "Recent notifications will appear here"}</span></div>}</div>}
      {mode === "system" && <div className="top-system"><div className="top-title"><DeckIcon name="monitor" size={16} /><strong>{fr ? "Votre ordinateur" : "Your computer"}</strong></div><div className="system-metrics"><div><small>CPU</small><strong>{typeof cpu === "number" ? `${cpu}%` : "—"}</strong><i><b style={{ width: typeof cpu === "number" ? `${cpu}%` : "0%" }} /></i></div><div><small>{fr ? "MÉMOIRE" : "MEMORY"}</small><strong>{typeof memory === "number" ? `${memory}%` : "—"}</strong><i><b style={{ width: typeof memory === "number" ? `${memory}%` : "0%" }} /></i></div></div><div className="active-app"><span><DeckIcon name="app" size={16} /></span><div><small>{fr ? "APPLICATION ACTIVE" : "ACTIVE APPLICATION"}</small><strong>{String(status?.snapshot?.active_app ?? "3Decks Agent")}</strong></div></div></div>}
      {!(["media", "notifications", "system"].includes(mode)) && <div className="top-page"><span><DeckIcon name={page.icon || "page"} size={38} /></span><strong>{localized(page.title, locale) || page.id}</strong><small>{fr ? "Cette page est prête" : "This page is ready"}</small></div>}
    </section>
  );
}

export function DeckPreview({ config, page, pageIndex, locale, selectedSlot, status, slots, t, onSelectPage, onSelectSlot, onMoveButton }: Props) {
  const dynamic = page.source === "windows";
  const fr = locale === "fr";
  const appItems = Array.isArray(status?.snapshot?.apps) ? status.snapshot.apps.map(String) : [];
  return (
    <div className="preview-column">
      <div className="workspace-heading">
        <div><span className="eyebrow">{t("page")} {pageIndex + 1}</span><h1>{localized(page.title, locale) || page.id}</h1><p>{fr ? "Touchez un emplacement dans l’écran du bas pour le configurer." : "Select a slot on the bottom screen to configure it."}</p></div>
        <span className="layout-chip"><DeckIcon name={page.layout === "list" ? "list" : "grid"} size={16} />{t(page.layout === "list" ? "list" : "grid")}</span>
      </div>
      <div className="device-stage">
        <div className="device-shell-wrap">
          <img className="device-shell-image" src="/device-shell.png" alt="" draggable={false} />
          <TopScreen page={page} status={status} locale={locale} />
          <section className="device-bottom-screen" aria-label={fr ? "Aperçu de l’écran tactile" : "Touch screen preview"}>
            <div className={`screen-content ${page.layout === "list" ? "list-mode" : "grid-mode"}`}>
              {dynamic && !appItems.length ? <div className="dynamic-empty"><span><DeckIcon name="app" size={25} /></span><strong>{fr ? "Fenêtres disponibles" : "Available windows"}</strong><p>{fr ? "Cette zone se remplira automatiquement avec les applications ouvertes sur votre ordinateur." : "This area fills automatically with apps open on your computer."}</p></div> : null}
              {page.layout === "list" ? (
                <div className="console-list">
                  {(dynamic ? appItems : page.buttons).slice(0, slots).map((item, index) => {
                    const button = typeof item === "object" && item && "slot" in item ? item as PageConfig["buttons"][number] : null;
                    const label = button ? localized(button.label, locale) : String(item);
                    return <button key={button?.id ?? label} type="button" onClick={() => button && onSelectSlot(button.slot)}><span><DeckIcon name={button?.icon ?? "app"} size={16} /></span><strong>{label}</strong><small>›</small></button>;
                  })}
                  {!dynamic && !page.buttons.length && <button type="button" className="list-empty" onClick={() => onSelectSlot(0)}><DeckIcon name="plus" size={16} />{t("addAction")}</button>}
                </div>
              ) : !dynamic || appItems.length ? (
                <div className="console-grid">
                  {Array.from({ length: slots }, (_, slot) => {
                    const button = page.buttons.find((item) => item.slot === slot);
                    const dynamicLabel = dynamic && !button ? appItems[slot] ?? "" : "";
                    return (
                      <button
                        key={slot}
                        type="button"
                        className={`${button ? "configured" : "empty"} ${selectedSlot === slot ? "selected" : ""} ${dynamicLabel ? "dynamic" : ""}`}
                        style={button ? { "--button-color": button.color } as CSSProperties : undefined}
                        draggable={Boolean(button)}
                        onDragStart={(event) => event.dataTransfer.setData("text/deck-slot", String(slot))}
                        onDragOver={(event) => { if (event.dataTransfer.types.includes("text/deck-slot")) event.preventDefault(); }}
                        onDrop={(event) => { event.preventDefault(); onMoveButton(Number(event.dataTransfer.getData("text/deck-slot")), slot); }}
                        onClick={() => onSelectSlot(slot)}
                      >
                        <span className="console-button-icon"><DeckIcon name={button?.icon ?? (dynamicLabel ? "app" : "plus")} size={20} /></span>
                        <strong>{button ? localized(button.label, locale) : dynamicLabel || t("emptySlot")}</strong>
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
      <p className="preview-caption"><DeckIcon name="info" size={16} />{fr ? "Aperçu fidèle de vos deux écrans. Glissez les actions pour les réorganiser." : "Accurate preview of both screens. Drag actions to reorder them."}</p>
    </div>
  );
}
