export type Locale = "fr" | "en";
export type View = "editor" | "settings" | "status";
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
  type: "text" | "number" | "hotkey" | "page" | "script";
  required: boolean;
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
  dashboards: Array<{ name: string; supported: boolean }>;
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

export interface AgentState {
  version: string;
  platform: string;
  listen: string;
  hints: string[];
  token_set: boolean;
  clients: Array<{ id: string; address: string }>;
  capabilities: Record<string, boolean>;
  features: Record<string, boolean>;
  notifications?: { access?: string; enabled?: boolean; available?: boolean };
  snapshot?: Record<string, unknown>;
  logs: string[];
}
