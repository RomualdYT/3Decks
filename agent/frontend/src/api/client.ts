import type { AgentState, DeckConfig, ObsConfig, Schema } from "../app/types";

type PairingState = AgentState["pairing"];

const TOKEN_KEY = "deck3ds.token";

function readToken(): string {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get("token");
  if (fromUrl) {
    try { sessionStorage.setItem(TOKEN_KEY, fromUrl); } catch { /* memory-only */ }
    history.replaceState(null, "", window.location.pathname);
    return fromUrl;
  }
  try { return sessionStorage.getItem(TOKEN_KEY) ?? ""; } catch { return ""; }
}

let token = readToken();

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "X-Deck3DS-Token": token };
  const options: RequestInit = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const text = await response.text();
  let payload: Record<string, unknown> = {};
  try { payload = text ? JSON.parse(text) as Record<string, unknown> : {}; }
  catch { throw new Error(`Réponse illisible de l’agent : ${text.slice(0, 160)}`); }
  if (response.status === 403) {
    token = "";
    try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* already gone */ }
    throw new Error("Le lien de configuration a expiré. Rouvrez celui affiché par l’agent.");
  }
  if (!response.ok) throw new Error(String(payload.error ?? `Erreur HTTP ${response.status}`));
  return payload as T;
}

export const agentApi = {
  schema: () => request<Schema>("GET", "/api/schema"),
  config: () => request<{ config: DeckConfig; path: string }>("GET", "/api/config"),
  save: (config: DeckConfig) => request<{ saved: boolean; config: DeckConfig }>("PUT", "/api/config", config),
  state: () => request<AgentState>("GET", "/api/state"),
  apps: () => request<{ apps: string[] }>("GET", "/api/apps"),
  pickPath: (kind: "file" | "folder") => request<{ cancelled: boolean; path: string; kind: "file" | "folder" }>("POST", "/api/paths/pick", { kind }),
  rotatePairing: () => request<PairingState>("POST", "/api/pairing/rotate"),
  openPermissionSettings: (permission: string) => request<{ opened: boolean; permission: string }>("POST", "/api/permissions/open", { permission }),
  testObs: (config: ObsConfig) => request<{ connected: boolean; obs_version?: string; current_scene?: string; scenes?: string[] }>("POST", "/api/obs/test", config),
};
