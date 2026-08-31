export type Locale = "fr" | "en";
export type View = "editor" | "settings" | "status" | "extensions";
export type Localized = string | Partial<Record<Locale, string>>;
export type ActionValue = string | ({ type: string } & Record<string, unknown>);

export interface ButtonConfig {
  id: string;
  slot: number;
  label: Localized;
  icon: string;
  color: string;
  toggle?: string;
  action: ActionValue;
  hold_label?: Localized;
  hold_action?: ActionValue;
}

export interface PageConfig {
  id: string;
  title: Localized;
  icon: string;
  dashboard: string;
  layout?: "grid" | "list";
  source?: string;
  buttons: ButtonConfig[];
}

export interface ObsConfig {
  enabled: boolean;
  host: string;
  port: number;
  password: string;
  timeout: number;
}

export interface DeckConfig {
  revision: number;
  server: {
    host: string;
    port: number;
    token: string;
    poll_interval: number;
    volume_step: number;
  };
  features: Record<string, boolean>;
  integrations: { obs: ObsConfig };
  pages: PageConfig[];
  scripts?: Record<string, string[]>;
}

export interface ActionArgument {
  name: string;
  type: "text" | "number" | "hotkey" | "page" | "script" | "password" | "boolean" | "select";
  required: boolean;
  label?: Localized;
  description?: Localized;
  default?: string | number | boolean;
  min?: number;
  max?: number;
  choices?: Array<{ value: string; label: Localized }>;
}

export interface ActionSpec {
  kind: string;
  category: string;
  icon: string;
  color: string;
  title: Record<Locale, string>;
  description: Record<Locale, string>;
  arguments: ActionArgument[];
  supported: boolean;
  capability: string | null;
  extension?: string;
  extension_name?: Localized;
}

export interface FeatureSpec {
  key: string;
  title: Record<Locale, string>;
  description: Record<Locale, string>;
  parent: string | null;
  platforms: string[];
  enabled: boolean;
  available: boolean;
}

export interface Schema {
  actions: ActionSpec[];
  features: FeatureSpec[];
  icons: string[];
  keys: {
    modifiers: Array<{ name: string; label_en: string; label_fr: string }>;
    groups: string[];
    keys: Array<{ name: string; label_en: string; label_fr: string; group: string }>;
  };
  dashboards: Array<{ name: string; supported: boolean; title?: Localized; description?: Localized; icon?: string }>;
  extension_sources?: Array<{ name: string; supported: boolean; title: Localized; description: Localized; icon: string }>;
  layouts: string[];
  sources: string[];
  capabilities: Record<string, boolean>;
  limits: Record<string, number | number[]> & {
    pages: number;
    buttons_per_page: number;
    label: number;
    id: number;
  };
  defaults: Record<string, string | number>;
}

export interface ExtensionManifest {
  api_version: number;
  id: string;
  version: string;
  name: Localized;
  description: Localized;
  author: string;
  platforms: string[];
  permissions: string[];
  settings: ActionArgument[];
  actions: Array<{ id: string; title: Localized; description: Localized }>;
  sources: Array<{ id: string; title: Localized; description: Localized }>;
  dashboards: Array<{ id: string; title: Localized; description: Localized }>;
}

export interface InstalledExtension {
  manifest: ExtensionManifest;
  digest: string;
  enabled: boolean;
  status: string;
  error: string;
  updated_at: number;
  settings: Record<string, unknown>;
  secret_fields_set: string[];
}

export interface ExtensionCatalog {
  api_version: number;
  directory: string;
  extensions: InstalledExtension[];
  errors: string[];
}

export interface AgentState {
  version: string;
  platform: string;
  listen: string;
  hints: string[];
  token_set: boolean;
  pairing: {
    required: boolean;
    code: string;
    expires_in: number;
  };
  discovery_port: number;
  clients: Array<{ id: string; address: string }>;
  capabilities: Record<string, boolean>;
  features: Record<string, boolean>;
  notifications?: {
    access?: string;
    enabled?: boolean;
    available?: boolean;
    error?: string;
    settings_action?: string;
  };
  snapshot?: Record<string, unknown>;
  logs: string[];
}
