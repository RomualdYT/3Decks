import { useEffect, useId, useState, type CSSProperties } from "react";
import type { AgentState, Locale, PageConfig } from "../app/types";
import { agentApi } from "../api/client";
import { DeckIcon } from "../components/DeckIcon";
import { SpotifyIcon, AppleMusicIcon } from "../components/BrandIcons";
import { ExtensionPreview } from "../extensions/ExtensionPreview";

type Data = Record<string, unknown>;
const record = (value: unknown): Data => value && typeof value === "object" && !Array.isArray(value) ? value as Data : {};
const string = (value: unknown, fallback = "") => typeof value === "string" && value ? value : fallback;
const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
const list = (value: unknown): unknown[] => Array.isArray(value) ? value : [];
export const mediaTime = (value: unknown) => {
  const seconds = Math.floor(number(value) ?? 0);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};
export function dashboardMode(page: PageConfig, media: Data): string {
  return !page.dashboard || page.dashboard === "auto" ? (media.title ? "media" : "apps") : page.dashboard;
}

function useArtwork(token: number | null) {
  const [image, setImage] = useState<{ token: number; url: string } | null>(null);
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    let url: string | undefined;
    void agentApi.artwork(controller.signal).then((blob) => {
      if (!blob || controller.signal.aborted) return;
      url = URL.createObjectURL(blob);
      setImage({ token, url });
    }).catch(() => { /* A missing image keeps the console's placeholder. */ });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [token]);
  return image?.token === token ? image.url : undefined;
}

function Label({ x, y, width, size = 14, color = "#a2a2aa", bold = false, align = "left", children }: {
  x: number; y: number; width: number; size?: number; color?: string; bold?: boolean;
  align?: "left" | "center" | "right"; children: React.ReactNode;
}) {
  return <foreignObject x={x} y={y} width={width} height={size * 1.5}>
    <div className="console-top-label" style={{ fontSize: size, color, fontWeight: bold ? 700 : 400, textAlign: align }}>{children}</div>
  </foreignObject>;
}
function Icon({ name, x, y, size = 18, color = "#66CB10" }: { name: string; x: number; y: number; size?: number; color?: string }) {
  return <g transform={`translate(${x}, ${y})`} color={color}><DeckIcon name={name} size={size} /></g>;
}
function Equalizer({ x, y, width, height, playing }: { x: number; y: number; width: number; height: number; playing: boolean }) {
  return <g aria-hidden="true" className={playing ? "console-equalizer playing" : "console-equalizer"}>
    {Array.from({ length: 16 }, (_, i) => {
      const h = playing ? height * (0.23 + ((i * 7) % 13) / 18) : 2;
      return <rect key={i} x={x + i * width / 16} y={y + height - h} width={width / 16 - 2.2} height={h} rx={2.5}
        fill="var(--media-accent)" style={{ animationDelay: `${i * -0.17}s`, transformOrigin: `${x + i * width / 16}px ${y + height}px` }} />;
    })}
  </g>;
}
function Track({ x, y, width, ratio, color = "var(--media-accent)" }: { x: number; y: number; width: number; ratio: number; color?: string }) {
  const filled = width * Math.max(0, Math.min(1, ratio));
  return <g><rect x={x} y={y} width={width} height={5} rx={2.5} fill="#34343a" />
    {filled > 0 && <rect x={x} y={y} width={filled} height={5} rx={2.5} fill={color} />}</g>;
}
function Media({ media, frame, fr }: { media: Data; frame: boolean; fr: boolean }) {
  const image = useArtwork(number(media.art));
  if (!media.title) return <g><Icon name="music" x={180} y={94} size={40} color="#686872" />
    <Label x={30} y={162} width={340} align="center">{fr ? "Aucune lecture en cours" : "Nothing playing"}</Label></g>;
  const art = frame ? 206 : 174, y = frame ? 17 : 48, x = frame ? 242 : 211, width = 384 - x;
  const app = string(media.app, fr ? "Musique" : "Music");
  const spotify = /spotify/i.test(app), apple = /apple|music/i.test(app);
  const position = number(media.position) ?? 0, duration = number(media.duration) ?? 0;
  const brandY = frame ? 35 : 49;
  return <g>
    <rect x={14} y={y - 4} width={art + 8} height={art + 8} rx={8} fill="var(--media-accent)" opacity={0.16} />
    <rect x={18} y={y} width={art} height={art} rx={5} fill="#0d0d0f" stroke="var(--media-accent)" strokeOpacity={0.65} />
    {image ? <image href={image} x={20} y={y + 2} width={art - 4} height={art - 4} preserveAspectRatio="xMidYMid meet" /> :
      <Icon name="music" x={18 + art * .3} y={y + art * .3} size={art * .4} />}
    <rect x={x} y={brandY} width={Math.min(width, app.length * 7 + 30)} height={18} rx={9} fill="#0d0d0f" fillOpacity={.65} />
    <g transform={`translate(${x + 2}, ${brandY + 1})`}>{spotify ? <SpotifyIcon size={16} /> : apple ? <AppleMusicIcon size={16} /> : <DeckIcon name="music" size={16} />}</g>
    <Label x={x + 22} y={brandY + 1} width={width - 22} size={12.6}>{app}</Label>
    <Label x={x} y={frame ? 60 : 74} width={width} size={20} color="#f6f6f7" bold>{string(media.title)}</Label>
    <Label x={x} y={frame ? 86 : 101} width={width} size={15.6}>{string(media.artist)}</Label>
    <Label x={x} y={frame ? 106 : 121} width={width} size={13.8} color="#868690">{string(media.album)}</Label>
    <Equalizer x={x} y={frame ? 133 : 151} width={width} height={33} playing={media.playing === true} />
    {duration > 0 && <g><Track x={x} y={frame ? 197 : 199} width={width} ratio={position / duration} />
      <Label x={x} y={208} width={width / 2} size={13.8}>{mediaTime(Math.min(position, duration))}</Label>
      <Label x={x + width / 2} y={208} width={width / 2} size={13.8} align="right">{mediaTime(duration)}</Label></g>}
  </g>;
}
function Audio({ snapshot, media, fr }: { snapshot: Data; media: Data; fr: boolean }) {
  const volume = number(snapshot.volume), music = number(snapshot.app_volume);
  const output = string(snapshot.audio_output, fr ? "Sortie inconnue" : "Unknown output");
  const outputs = list(snapshot.audio_outputs).map(item => string(item)).filter(Boolean);
  return <g>
    <rect x={12} y={36} width={376} height={150} rx={10} fill="#1a1a1e" />
    <rect x={24} y={45} width={352} height={34} rx={10} fill="#0d0d0f" />
    <Icon name="volume-up" x={32} y={53} />
    <Label x={55} y={46} width={300} size={12} color="#686872">{fr ? "SORTIE AUDIO" : "AUDIO OUTPUT"}</Label>
    <Label x={55} y={60} width={300} size={13.8}>{output}</Label>
    <Label x={28} y={84} width={340} size={12.6}>{outputs.join("  ·  ")}</Label>
    <Equalizer x={28} y={105} width={344} height={63} playing={media.playing === true && snapshot.muted !== true} />
    <rect x={0} y={194} width={400} height={46} fill="#121214" />
    {[{ x: 8, w: music === null ? 272 : 133, label: fr ? "Système" : "System", value: volume },
      ...(music === null ? [] : [{ x: 147, w: 133, label: fr ? "Musique" : "Music", value: music }])].map(item =>
      <g key={item.label}><rect x={item.x} y={200} width={item.w} height={34} rx={9} fill="#242428" />
        <Label x={item.x + 8} y={203} width={item.w - 48} size={12.6}>{item.label}</Label>
        <Label x={item.x + item.w - 46} y={203} width={38} size={12.6} align="right">{item.value === null ? "—" : `${Math.round(item.value)}%`}</Label>
        <Track x={item.x + 8} y={225} width={item.w - 16} ratio={(item.value ?? 0) / 100} /></g>)}
    <rect x={286} y={200} width={106} height={34} rx={17} fill="#242428" />
    <Icon name={snapshot.mic_muted ? "mic-off" : "mic"} x={296} y={208} color={snapshot.mic_muted ? "#f0747c" : "#45c995"} />
    <Label x={319} y={209} width={66} size={12.6}>{snapshot.mic_muted ? (fr ? "Coupé" : "Muted") : typeof snapshot.mic_muted === "boolean" ? "Live" : "—"}</Label>
  </g>;
}
function System({ snapshot, fr }: { snapshot: Data; fr: boolean }) {
  const cpu = number(snapshot.cpu), memory = number(snapshot.memory);
  const busy = (cpu ?? 0) >= 75 || (memory ?? 0) >= 85;
  const cards = [
    { x: 12, y: 69, label: "CPU", value: cpu === null ? "—" : `${cpu}%`, ratio: cpu, detail: fr ? "Processeur" : "Processor" },
    { x: 206, y: 69, label: fr ? "Mémoire" : "Memory", value: memory === null ? "—" : `${memory}%`, ratio: memory, detail: number(snapshot.memory_total_mb) === null ? "" : `${((number(snapshot.memory_used_mb) ?? 0) / 1024).toFixed(1)} / ${((number(snapshot.memory_total_mb) ?? 0) / 1024).toFixed(1)} GB` },
    { x: 12, y: 141, label: fr ? "Réseau" : "Network", value: number(snapshot.network_down_kbps) === null ? "—" : `↓ ${Math.round(number(snapshot.network_down_kbps)!)} KB/s`, ratio: null, detail: number(snapshot.network_up_kbps) === null ? "" : `↑ ${Math.round(number(snapshot.network_up_kbps)!)} KB/s` },
    { x: 206, y: 141, label: fr ? "Stockage" : "Storage", value: number(snapshot.disk) === null ? "—" : `${snapshot.disk}%`, ratio: number(snapshot.disk), detail: number(snapshot.disk_free_mb) === null ? "" : `${Math.round(number(snapshot.disk_free_mb)! / 1024)} GB ${fr ? "libres" : "free"}` },
  ];
  return <g><rect x={12} y={36} width={376} height={27} rx={9} fill={busy ? "#403319" : "#173325"} />
    <Label x={24} y={41} width={350} color="#f6f6f7">{cpu === null && memory === null ? (fr ? "En attente des mesures" : "Waiting for metrics") : busy ? (fr ? "Ordinateur sollicité" : "Computer busy") : (fr ? "Tout fonctionne bien" : "Running smoothly")}</Label>
    {cards.map(card => <g key={card.label}><rect x={card.x} y={card.y} width={182} height={66} rx={9} fill="#1a1a1e" />
      <Label x={card.x + 10} y={card.y + 4} width={162} size={12.6}>{card.label}</Label>
      <Label x={card.x + 10} y={card.y + 20} width={162} size={21} bold color="#f6f6f7">{card.value}</Label>
      <Label x={card.x + 10} y={card.y + 44} width={162} size={11.8}>{card.detail}</Label>
      {card.ratio !== null && <Track x={card.x + 10} y={card.y + 60} width={162} ratio={card.ratio / 100} color="#66CB10" />}</g>)}
    <rect x={12} y={214} width={376} height={18} rx={7} fill="#1a1a1e" />
    <Label x={22} y={215} width={355} size={12.6}>{fr ? "Processus" : "Process"} · {string(snapshot.top_process, "—")}</Label>
  </g>;
}
export function ConsoleTopScreen({ page, status, locale }: { page: PageConfig; status: AgentState | null; locale: Locale }) {
  const fr = locale === "fr", snapshot = record(status?.snapshot), media = record(snapshot.media);
  const mode = dashboardMode(page, media), frame = mode === "frame";
  const id = useId();
  const accent = /^#[0-9a-f]{6}$/i.test(string(media.accent)) ? string(media.accent) : /spotify/i.test(string(media.app)) ? "#1ed760" : /music/i.test(string(media.app)) ? "#fa3d58" : "#66cb10";
  const notifications = list(snapshot.notifications).map(record);
  const count = number(snapshot.notification_count) ?? notifications.length;
  const apps = list(snapshot.apps).map(item => string(item)).filter(Boolean);
  const date = new Intl.DateTimeFormat(fr ? "fr-FR" : "en-US", { month: "long", day: "numeric" }).format(new Date());
  const clock = string(snapshot.time, "—");
  return <section className="device-top-screen console-top-faithful" aria-label={fr ? "Aperçu de l’écran supérieur" : "Top screen preview"} data-dashboard={mode} style={{ "--media-accent": accent } as CSSProperties}>
    <svg viewBox="0 0 400 240" width="100%" height="100%" role="img" aria-label={fr ? "Écran supérieur de la console" : "Console top screen"}>
      <defs><linearGradient id={id} x2="0" y2="1"><stop stopColor={mode === "media" || frame ? accent : "#0d0d0f"} stopOpacity={mode === "media" || frame ? .2 : 1} /><stop offset="1" stopColor="#0d0d0f" /></linearGradient></defs>
      <rect width={400} height={240} fill="#0d0d0f" /><rect width={400} height={240} fill={`url(#${id})`} />
      {mode === "media" || frame ? <Media key={number(media.art) ?? 0} media={media} frame={frame} fr={fr} /> : mode === "audio" ? <Audio snapshot={snapshot} media={media} fr={fr} /> : mode === "system" ? <System snapshot={snapshot} fr={fr} /> : mode === "notifications" ?
        <g><Label x={16} y={40} width={365} size={20} bold color="#f6f6f7">Notifications</Label>
          {notifications.length ? notifications.slice(0, 3).map((item, i) => <g key={i}><rect x={12} y={72 + i * 51} width={376} height={46} rx={8} fill="#1a1a1e" /><Icon name="chat" x={23} y={85 + i * 51} color="#ffb020" /><Label x={50} y={76 + i * 51} width={325} bold>{string(item.app, "Notification")}</Label><Label x={50} y={95 + i * 51} width={325} size={12.6}>{string(item.title)}</Label></g>) :
            <Label x={20} y={124} width={360} align="center">{fr ? "Aucune notification" : "No notifications"}</Label>}</g> :
        mode.startsWith("ext:") ? <foreignObject x={12} y={36} width={376} height={196}><ExtensionPreview dashboard={mode} status={status} locale={locale} /></foreignObject> :
          <g><rect x={12} y={36} width={376} height={196} rx={10} fill="#1a1a1e" /><Icon name="app" x={27} y={54} size={28} />
            <Label x={68} y={49} width={300} size={12.6}>{fr ? "APPLICATION ACTIVE" : "FOREGROUND"}</Label>
            <Label x={68} y={67} width={300} size={20} bold color="#f6f6f7">{string(snapshot.active_app, fr ? "Aucune application" : "No application")}</Label>
            {apps.slice(0, 4).map((app, i) => <Label key={i} x={28} y={110 + i * 26} width={342}>{app}</Label>)}</g>}
      {!frame ? <g><Label x={12} y={7} width={85} size={20} bold color="#f6f6f7">{clock}</Label>
        <Label x={109} y={11} width={130} size={13.8} align="center">{date}</Label>
        <rect x={247} y={7} width={count ? 99 : 141} height={18} rx={9} fill="#1a1a1e" />
        <circle cx={256} cy={16} r={3} fill={status?.clients.length ? "#45c995" : "#a2a2aa"} />
        <Label x={265} y={8} width={count ? 78 : 115} size={12.6}>{status?.clients.length ? (fr ? "Connecté" : "Connected") : (fr ? "Aperçu" : "Preview")}</Label>
        {count > 0 && <g><Icon name="chat" x={354} y={10} size={12} color="#ffb020" /><Label x={370} y={8} width={22} size={12.6}>{count}</Label></g>}
      </g> : <Label x={302} y={16} width={82} align="right" size={13.8}>{clock}</Label>}
    </svg>
  </section>;
}
