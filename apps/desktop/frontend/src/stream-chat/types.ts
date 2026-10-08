export interface StreamChatSettings {
  enabled: boolean;
  channel: string;
  client_id: string;
  timestamps: boolean;
  hide_commands: boolean;
  compact: boolean;
}

export interface StreamChatBadge {
  token: number;
  title: string;
  image: string;
}

export interface StreamChatMessage {
  id: string;
  user_id: string;
  author: string;
  text: string;
  color: string;
  time: string;
  badges: StreamChatBadge[];
}

export interface StreamChatSnapshot {
  provider: "twitch";
  channel: string;
  status: string;
  timestamps: boolean;
  compact: boolean;
  messages: StreamChatMessage[];
}

export interface StreamChatView {
  settings: StreamChatSettings;
  snapshot: StreamChatSnapshot;
  account: string;
  configured: boolean;
  supported: boolean;
  error: string | null;
  authorization: { code: string; url: string; expires_in: number } | null;
}
