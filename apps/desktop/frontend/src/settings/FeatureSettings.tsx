import { Switch, toast } from "@heroui/react";
import { useEffect, useState } from "react";
import type { NotificationPermissionStatus } from "../app/desktopControls";
import { agentApi } from "../api/client";
import type { AgentState, DeckConfig, FeatureSpec, Locale, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { DeckIcon } from "../components/DeckIcon";
import { AppleMusicIcon, SpotifyIcon } from "../components/BrandIcons";
import { AudioOutputSettings } from "./AudioOutputSettings";
import { FeaturePermissionNotice } from "./FeaturePermissionNotice";
import { notificationPermissionError } from "../utils/notificationPermission";

const FEATURE_ICONS: Record<string, string> = {
  notifications: "bell", windows: "app", system_stats: "status",
  audio_output: "volume-up", media_artwork: "artwork",
};

interface FeatureSettingsProps {
  config: DeckConfig;
  schema: Schema;
  status: AgentState | null;
  locale: Locale;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  update: (recipe: (draft: DeckConfig) => void) => void;
}

export function FeatureSettings({ config, schema, status, locale, t, update }: FeatureSettingsProps) {
  const native = import.meta.env.VITE_DECKS_DESKTOP === "1";
  const [openingPermission, setOpeningPermission] = useState<string | null>(null);
  const [notificationAccess, setNotificationAccess] = useState<NotificationPermissionStatus | null>(null);
  const [requestingNotifications, setRequestingNotifications] = useState(false);
  const openPermission = (permission: string) => {
    setOpeningPermission(permission);
    void agentApi.openPermissionSettings(permission)
      .then(() => toast.success(t("permissionsOpened")))
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setOpeningPermission(null));
  };
  const groups: Array<{ title: string; icon: string; items: FeatureSpec[] }> = [
    { title: locale === "fr" ? "Informations système" : "System information", icon: "monitor", items: schema.features.filter((item) => ["notifications", "windows", "system_stats", "audio_output"].includes(item.key)) },
    { title: locale === "fr" ? "Média et lecteurs" : "Media and players", icon: "music", items: schema.features.filter((item) => ["media", "lyrics_online", "media_artwork", "apple_music", "spotify"].includes(item.key)) },
  ];
  useEffect(() => setNotificationAccess(null), [status?.notifications?.access]);
  const currentNotificationAccess = notificationAccess ?? status?.notifications;
  const requestNotificationAccess = async () => {
    const controls = window.decksDesktopControls;
    if (!controls) return;
    setRequestingNotifications(true);
    try {
      const result = await controls.requestNotificationAccess();
      setNotificationAccess(result.status);
      if (result.access === "Allowed") toast.success(locale === "fr" ? "Accès aux notifications autorisé" : "Notification access allowed");
      else toast.danger(locale === "fr" ? "Accès aux notifications refusé" : "Notification access was denied");
    } catch (error) {
      toast.danger(error instanceof Error ? error.message : String(error));
    } finally {
      setRequestingNotifications(false);
    }
  };
  return (
    <div className="settings-content">
      <div className="settings-title">
        <span><DeckIcon name="sliders" size={24} /></span>
        <div><h1>{t("featureTitle")}</h1><p>{t("featureHelp")}</p></div>
      </div>
      {groups.map((group) => (
        <section className="feature-group" key={group.title}>
          <div className="feature-group-title"><DeckIcon name={group.icon} /><h2>{group.title}</h2></div>
          {group.items.map((feature) => {
            const parentEnabled = !feature.parent || config.features[feature.parent] !== false;
            const enabled = config.features[feature.key] ?? feature.enabled;
            const platformAvailable = !status?.platform || feature.platforms.includes(status.platform);
            const isNotification = feature.key === "notifications";
            const requestNotifications = native && status?.platform === "win32" && isNotification && enabled && currentNotificationAccess?.access === "Unspecified";
            const permissionAction = isNotification && enabled && currentNotificationAccess?.available === false ? currentNotificationAccess.settings_action : undefined;
            const icon = FEATURE_ICONS[feature.key] ?? "music";
            return (
              <div className={`feature-row ${requestNotifications || permissionAction || (native && platformAvailable && enabled && feature.key === "audio_output") ? "has-details" : ""} ${feature.parent ? "nested" : ""} ${!platformAvailable ? "unavailable" : ""}`} key={feature.key}>
                <div className={`feature-symbol ${feature.key === "spotify" || feature.key === "apple_music" ? "brand" : ""}`}>
                  {feature.key === "spotify" ? <SpotifyIcon /> : feature.key === "apple_music" ? <AppleMusicIcon /> : <DeckIcon name={icon} />}
                </div>
                <div className="feature-copy">
                  <h3>{feature.title[locale]}</h3>
                  <p>{feature.description[locale]}</p>
                  {!platformAvailable && <small>{t("unavailablePlatform")}</small>}
                  {isNotification && !permissionAction && !requestNotifications && currentNotificationAccess?.error && <small className="feature-detail-note">{notificationPermissionError(currentNotificationAccess.access, currentNotificationAccess.error, locale)}</small>}
                  {requestNotifications ? <FeaturePermissionNotice
                    title={locale === "fr" ? "Autorisation nécessaire" : "Permission needed"}
                    description={locale === "fr" ? "Autorisez 3Decks à lire les notifications Windows pour les afficher sur votre console." : "Allow 3Decks to read Windows notifications and show them on your console."}
                    action={requestingNotifications ? t("openingPermissions") : locale === "fr" ? "Autoriser" : "Allow access"}
                    busy={requestingNotifications} onAction={() => void requestNotificationAccess()} /> : permissionAction ? <FeaturePermissionNotice
                    title={locale === "fr" ? "Accès aux notifications requis" : "Notification access needed"}
                    description={locale === "fr" ? "Autorisez 3Decks à lire vos notifications dans les réglages système." : "Allow 3Decks to read your notifications in system settings."}
                    action={openingPermission === permissionAction ? t("openingPermissions") : locale === "fr" ? "Ouvrir les réglages" : "Open settings"}
                    busy={openingPermission === permissionAction} onAction={() => openPermission(permissionAction)} /> : null}
                  {native && platformAvailable && enabled && feature.key === "audio_output" && (
                    <AudioOutputSettings locale={locale} windows={status?.platform === "win32"} />
                  )}
                </div>
                <div className="feature-state">
                  <span>{enabled && parentEnabled ? t("enabled") : t("disabled")}</span>
                  <Switch aria-label={feature.title[locale]} isSelected={enabled && parentEnabled} isDisabled={!platformAvailable || !parentEnabled} onChange={(selected) => update((draft) => { draft.features[feature.key] = selected; })}>
                    <Switch.Content><Switch.Control><Switch.Thumb /></Switch.Control></Switch.Content>
                  </Switch>
                </div>
              </div>
            );
          })}
        </section>
      ))}
    </div>
  );
}
