import "./stream-chat.css";
import { useEffect, useRef, useState } from "react";
import { Button } from "@heroui/react";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { chatStatus } from "./copy";
import { StreamChatBadges } from "./StreamChatBadges";
import type { StreamChatSnapshot } from "./types";

export function StreamChatFeed({
  snapshot,
  locale,
  console = false,
}: {
  snapshot?: StreamChatSnapshot;
  locale: Locale;
  console?: boolean;
}) {
  const fr = locale === "fr";
  const [paused, setPaused] = useState(false);
  const feed = useRef<HTMLDivElement>(null);
  const messages = snapshot?.messages ?? [];
  const last = messages.at(-1)?.id;
  useEffect(() => {
    if (!paused && feed.current)
      feed.current.scrollTop = feed.current.scrollHeight;
  }, [last, paused]);
  useEffect(() => setPaused(false), [snapshot?.channel]);
  return (
    <div
      className={`stream-chat-feed${console ? " console-chat-feed" : ""}${snapshot?.compact ? " compact" : ""}`}
    >
      <header>
        <span className="stream-chat-provider">
          <DeckIcon name="chat" size={console ? 14 : 18} />
          <strong>
            {snapshot?.channel ? `#${snapshot.channel}` : "Twitch"}
          </strong>
        </span>
        <span
          className={`stream-chat-status ${snapshot?.status === "connected" ? "connected" : ""}`}
        >
          {chatStatus(snapshot?.status ?? "disabled", locale)}
        </span>
      </header>
      <div
        ref={feed}
        className="stream-chat-messages"
        role="log"
        aria-label={fr ? "Messages du chat" : "Chat messages"}
        aria-live={paused ? "off" : "polite"}
        aria-relevant="additions removals"
        onWheel={(event) => {
          if (event.deltaY < 0) setPaused(true);
        }}
        onScroll={(event) => {
          const element = event.currentTarget;
          if (
            element.scrollHeight - element.scrollTop - element.clientHeight >
            8
          )
            setPaused(true);
        }}
      >
        {messages.length ? (
          messages.map((message) => (
            <article key={message.id} className="stream-chat-message">
              <div className="stream-chat-author">
                {snapshot?.timestamps && (
                  <time title="UTC">{message.time}</time>
                )}
                <StreamChatBadges badges={message.badges} size={console ? 12 : 16} />
                <strong
                  style={{
                    color: /^#[\da-f]{6}$/i.test(message.color)
                      ? message.color
                      : "#bda4ff",
                  }}
                >
                  {message.author}
                </strong>
              </div>
              <p>{message.text}</p>
            </article>
          ))
        ) : (
          <div className="stream-chat-empty">
            <DeckIcon name="chat" size={console ? 24 : 32} />
            <strong>
              {snapshot?.status === "connected"
                ? fr
                  ? "En attente des messages"
                  : "Waiting for messages"
                : chatStatus(snapshot?.status ?? "disabled", locale)}
            </strong>
            <p>
              {snapshot?.status === "connected"
                ? fr
                  ? "Les nouveaux messages apparaîtront ici."
                  : "New messages will appear here."
                : fr
                  ? "Configurez le chat dans Réglages → Streaming."
                  : "Set up chat in Settings → Streaming."}
            </p>
          </div>
        )}
      </div>
      <footer>
        <span>
          {paused
            ? fr
              ? "Défilement suspendu"
              : "Scrolling paused"
            : fr
              ? "Nouveaux messages"
              : "Following chat"}
          {snapshot?.timestamps ? " · UTC" : ""}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onPress={() => setPaused((value) => !value)}
          aria-label={
            paused
              ? fr
                ? "Reprendre le défilement"
                : "Resume scrolling"
              : fr
                ? "Suspendre le défilement"
                : "Pause scrolling"
          }
        >
          <DeckIcon name={paused ? "play" : "pause"} size={console ? 11 : 15} />
          {paused ? (fr ? "Reprendre" : "Resume") : fr ? "Pause" : "Pause"}
        </Button>
      </footer>
    </div>
  );
}
