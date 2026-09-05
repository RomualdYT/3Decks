import type { AgentState, DeckConfig, ObsConfig, Schema, ExtensionCatalog } from "../app/types";
import type { components, operations } from "./generated";

export type ExtensionRequest = operations["manage_extension"]["requestBody"]["content"]["application/json"];

type PairingState = AgentState["pairing"];

const TOKEN_KEY = "deck3ds.token";

export class AgentApiError extends Error {
  constructor(message: string, public status: number, public code: string, public requestId: string) {
    super(message);
    this.name = "AgentApiError";
  }
}

function readToken(): string {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get("token");
  if (fromUrl) {
    try { sessionStorage.setItem(TOKEN_KEY, fromUrl); } catch { /* memory-only */ }
    history.replaceState(null, "", window.location.pathname + window.location.hash);
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
  if (response.status === 403 && payload.code === "invalid_session") {
    token = "";
    try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* already gone */ }
    throw new AgentApiError("Le lien de configuration a expiré. Rouvrez celui affiché par l’agent.", 403, "invalid_session", String(payload.request_id ?? ""));
  }
  if (!response.ok) throw new AgentApiError(String(payload.error ?? `Erreur HTTP ${response.status}`), response.status, String(payload.code ?? "http_error"), String(payload.request_id ?? ""));
  return payload as T;
}

export const agentApi = {
  health: () => request<components["schemas"]["Health"]>("GET", "/api/health"),
  validate: (config: DeckConfig) => request<components["schemas"]["ValidationResult"]>("POST", "/api/config/validate", config),
  extensions: () => request<ExtensionCatalog>("GET", "/api/extensions"),
  manageExtension: (body: ExtensionRequest) => request<components["schemas"]["OperationResult"]>("POST", "/api/extensions", body),
  schema: () => request<Schema>("GET", "/api/schema"),
  config: () => request<components["schemas"]["ConfigRead"]>("GET", "/api/config"),
  save: (config: DeckConfig) => request<components["schemas"]["ConfigSaved"]>("PUT", "/api/config", config),
  state: () => request<AgentState>("GET", "/api/state"),
  apps: () => request<components["schemas"]["Apps"]>("GET", "/api/apps"),
  pickPath: (kind: "file" | "folder") => request<components["schemas"]["PathSelection"]>("POST", "/api/paths/pick", { kind }),
  rotatePairing: () => request<PairingState>("POST", "/api/pairing/rotate"),
  revokePairedDevice: (deviceId: string) => request<components["schemas"]["DeviceRevoked"]>("DELETE", `/api/paired-devices/${encodeURIComponent(deviceId)}`),
  openPermissionSettings: (permission: string) => request<components["schemas"]["PermissionOpened"]>("POST", "/api/permissions/open", { permission }),
  testObs: (config: ObsConfig) => request<components["schemas"]["ObsStatus"]>("POST", "/api/obs/test", config),
};
