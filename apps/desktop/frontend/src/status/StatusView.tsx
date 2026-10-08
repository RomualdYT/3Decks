import { platformLabel } from "../utils/platform";
import { Card } from "@heroui/react";
import type { AgentState, Locale } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { DeckIcon } from "../components/DeckIcon";

export function StatusView({ status, locale, t }: { status: AgentState | null; locale: Locale; t: (key: CopyKey, values?: Record<string, string | number>) => string }) {
  if (!status) return <main className="status-workspace"><div className="empty-status"><DeckIcon name="wifi" size={38} /><h1>{t("offline")}</h1><p>{t("statusHelp")}</p></div></main>;
  const summary = [
    ["version", status.version], ["platform", platformLabel(status.platform)], ["listen", status.listen], ["address", status.hints.join(" · ") || "—"],
  ] as const;
  return <main className="status-workspace"><div className="status-content"><div className="settings-title"><span><DeckIcon name="status" size={24} /></span><div><h1>{t("statusTitle")}</h1><p>{t("statusHelp")}</p></div><div className={`status-online ${status.paused ? "paused" : ""}`}><span />{status.paused ? (locale === "fr" ? "Commandes suspendues" : "Controls suspended") : t("online")}</div></div>
    <div className="status-summary">{summary.map(([key, value]) => <Card key={key} variant="secondary"><Card.Content><small>{t(key)}</small><strong>{value}</strong></Card.Content></Card>)}</div>
    <section className="status-section"><div className="section-title"><h2>{t("capabilities")}</h2><span>{Object.values(status.capabilities).filter(Boolean).length}/{Object.keys(status.capabilities).length}</span></div><div className="capability-grid">{Object.entries(status.capabilities).map(([name, available]) => <div key={name}><span className={available ? "yes" : ""}><DeckIcon name={available ? "sparkle" : "close"} size={14} /></span><strong>{name.replaceAll("_", " ")}</strong><small>{available ? t("enabled") : t("disabled")}</small></div>)}</div></section>
    <section className="status-section"><div className="section-title"><h2>{t("logs")}</h2><span>{status.logs.length}</span></div><pre className="logs">{status.logs.slice(-100).join("\n") || (locale === "fr" ? "Aucun événement récent." : "No recent event.")}</pre></section>
  </div></main>;
}
