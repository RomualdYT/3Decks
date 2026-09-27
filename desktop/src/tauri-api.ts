import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import type { AgentState, DeckConfig, ExtensionCatalog, ObsConfig, Schema } from "../../frontend/src/app/types";
import type { components, operations } from "../../frontend/src/api/generated";

export type ExtensionRequest = operations["manage_extension"]["requestBody"]["content"]["application/json"];


export const agentApi = {
  artwork: async (_signal: AbortSignal): Promise<Blob | null> => {
    const bytes = await invoke<number[] | null>("get_artwork");
    return bytes ? new Blob([new Uint8Array(bytes)], { type: "image/png" }) : null;
  },
  health: async (): Promise<components["schemas"]["Health"]> => ({ status: "ready", components: {}, uptime: 0, last_collection_age: null }),
  validate: (config: DeckConfig) => invoke<components["schemas"]["ValidationResult"]>("validate_config", { document: config }),
  extensions: () => invoke<ExtensionCatalog>("get_extensions"),
  manageExtension: (request: ExtensionRequest) => invoke<components["schemas"]["OperationResult"]>("manage_extension", { request }),
  schema: () => invoke<Schema>("get_catalog"),
  config: async (): Promise<components["schemas"]["ConfigRead"]> => ({ config: await invoke<DeckConfig>("get_config"), path: "Configuration Tauri" }),
  save: async (config: DeckConfig): Promise<components["schemas"]["ConfigSaved"]> => ({ saved: true, config: await invoke<DeckConfig>("save_config", { document: config }) }),
  state: () => invoke<AgentState>("get_editor_state"),
  apps: () => invoke<components["schemas"]["Apps"]>("get_apps"),
  pickPath: async (kind: "file" | "folder"): Promise<components["schemas"]["PathSelection"]> => {
    const path = await open({ multiple: false, directory: kind === "folder" });
    return { cancelled: path === null, path: path ?? "", kind };
  },
  rotatePairing: () => invoke<AgentState["pairing"]>("rotate_pairing"),
  revokePairedDevice: (deviceId: string) => invoke<components["schemas"]["DeviceRevoked"]>("revoke_paired_device", { deviceId }),
  openPermissionSettings: (permission: string) => invoke<components["schemas"]["PermissionOpened"]>("open_permission_settings", { permission }),
  getAutostart: () => invoke<boolean>("get_autostart"),
  setAutostart: (enabled: boolean) => invoke<boolean>("set_autostart", { enabled }),
  testObs: (config: ObsConfig) => invoke<components["schemas"]["ObsStatus"]>("test_obs", { config }),
};
