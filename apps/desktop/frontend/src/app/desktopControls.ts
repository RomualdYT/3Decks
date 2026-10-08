/** Optional desktop-only controls installed by the Tauri entrypoint. */
export interface DesktopControls {
  windowFrame?: {
    minimize(): Promise<void>;
    toggleMaximize(): Promise<void>;
    isMaximized(): Promise<boolean>;
    close(): Promise<void>;
  };
  openCommunity(): Promise<void>;
  getAutostart(): Promise<boolean>;
  setAutostart(enabled: boolean): Promise<boolean>;
  getUpdateCapability(): Promise<{ configured: boolean; version: string }>;
  checkForUpdates(): Promise<{ available: boolean; version: string; notes?: string }>;
  installUpdate(): Promise<void>;
  getAudioOutputs(): Promise<AudioOutput[]>;
  selectAudioOutput(id: string): Promise<string>;
  openAudioSettings(): Promise<void>;
  requestNotificationAccess(): Promise<{ access: string; status: NotificationPermissionStatus }>;
}

export interface AudioOutput {
  id: string;
  name: string;
  is_default: boolean;
}

export interface NotificationPermissionStatus {
  access?: string;
  available?: boolean;
  enabled?: boolean;
  error?: string;
  settings_action?: string;
}

declare global {
  interface Window {
    decksDesktopControls?: DesktopControls;
  }
}
