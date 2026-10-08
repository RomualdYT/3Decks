import { useEffect, useRef, useState } from "react";
import type { StreamChatSettings, StreamChatView } from "./types";

const SETTINGS_KEYS = [
  "enabled",
  "channel",
  "client_id",
  "timestamps",
  "hide_commands",
  "compact",
] as const;

function sameSettings(left: StreamChatSettings, right: StreamChatSettings) {
  return SETTINGS_KEYS.every((key) => left[key] === right[key]);
}

// Merge server defaults without overwriting fields edited while authorization is pending.
function mergeSettings(
  current: StreamChatSettings | null,
  previous: StreamChatSettings | null,
  next: StreamChatSettings,
) {
  if (!current || !previous || sameSettings(current, previous)) return next;
  return {
    enabled:
      current.enabled === previous.enabled ? next.enabled : current.enabled,
    channel:
      current.channel === previous.channel ? next.channel : current.channel,
    client_id:
      current.client_id === previous.client_id
        ? next.client_id
        : current.client_id,
    timestamps:
      current.timestamps === previous.timestamps
        ? next.timestamps
        : current.timestamps,
    hide_commands:
      current.hide_commands === previous.hide_commands
        ? next.hide_commands
        : current.hide_commands,
    compact:
      current.compact === previous.compact ? next.compact : current.compact,
  };
}

export function useStreamChat() {
  const controls = window.decksDesktopControls;
  const [view, setView] = useState<StreamChatView | null>(null);
  const [draft, setDraft] = useState<StreamChatSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const serverSettings = useRef<StreamChatSettings | null>(null);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    if (!controls) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      const request = generation.current;
      try {
        if (document.visibilityState !== "hidden" && !inFlight.current) {
          const result = await controls.getStreamChat();
          if (
            !cancelled &&
            request === generation.current &&
            !inFlight.current
          ) {
            const previous = serverSettings.current;
            serverSettings.current = result.settings;
            setView(result);
            setDraft((current) =>
              mergeSettings(current, previous, result.settings),
            );
          }
        }
      } catch (reason) {
        if (!cancelled && request === generation.current && !inFlight.current)
          setError(String(reason));
      } finally {
        if (!cancelled) timer = setTimeout(() => void poll(), 1500);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      mounted.current = false;
      generation.current++;
      clearTimeout(timer);
    };
  }, [controls]);
  const dirty =
    draft !== null && view !== null && !sameSettings(draft, view.settings);
  const operate = async (
    operation: "save" | "authorize" | "disconnect" | "open",
  ) => {
    if (!controls || !draft || inFlight.current) return;
    inFlight.current = true;
    generation.current++;
    setBusy(true);
    setError("");
    try {
      let result = view;
      if (operation === "authorize") {
        result = await controls.configureStreamChat({
          ...draft,
          enabled: true,
        });
      } else if (operation === "save" && dirty) {
        result = await controls.configureStreamChat(draft);
      }
      if (operation === "authorize") {
        result = await controls.authorizeStreamChat();
        // One user action starts the grant and opens Twitch; the code remains visible in-app.
        if (result.authorization) {
          try {
            await controls.openStreamChatAuthorization();
          } catch (reason) {
            if (mounted.current) setError(String(reason));
          }
        }
      }
      if (operation === "disconnect")
        result = await controls.disconnectStreamChat();
      if (operation === "open") await controls.openStreamChatAuthorization();
      if (result && mounted.current) {
        setView(result);
        if (operation !== "open") {
          serverSettings.current = result.settings;
          setDraft(result.settings);
        }
      }
    } catch (reason) {
      if (mounted.current) setError(String(reason));
    } finally {
      generation.current++;
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  return { view, draft, setDraft, dirty, busy, error, operate };
}
