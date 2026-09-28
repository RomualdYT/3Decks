import type { operations } from "./generated";

export type ExtensionRequest = operations["manage_extension"]["requestBody"]["content"]["application/json"];
export type EditorApi = typeof import("./http").agentApi;

let implementation: EditorApi | null = null;

export function setEditorApi(api: EditorApi): void {
  implementation = api;
}

// Components depend on this stable boundary. The entry point selects the
// Tauri or HTTP adapter before React mounts, so no transport code leaks into UI.
export const agentApi: EditorApi = new Proxy({} as EditorApi, {
  get(_target, property) {
    if (!implementation) throw new Error("The editor API has not been initialized.");
    return Reflect.get(implementation, property);
  },
});
