/** Optional desktop-only controls installed by the Tauri entrypoint. */
export interface DesktopControls {
  getAutostart(): Promise<boolean>;
  setAutostart(enabled: boolean): Promise<boolean>;
  getUpdateCapability(): Promise<{ configured: boolean; version: string }>;
  checkForUpdates(): Promise<{ available: boolean; version: string; notes?: string }>;
  installUpdate(): Promise<void>;
}

declare global {
  interface Window {
    decksDesktopControls?: DesktopControls;
  }
}
