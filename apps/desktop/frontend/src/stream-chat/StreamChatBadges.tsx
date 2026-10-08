import type { StreamChatBadge } from "./types";

const IMAGE_URL = /^https:\/\/static-cdn\.jtvnw\.net\/badges\/v1\/[a-zA-Z0-9-]+\/[123]$/;

export function StreamChatBadges({
  badges = [],
  size,
}: {
  badges?: StreamChatBadge[];
  size: number;
}) {
  return badges.slice(0, 3).map((badge) =>
    IMAGE_URL.test(badge.image) ? (
      <img
        key={badge.token}
        className="stream-chat-badge"
        src={badge.image}
        alt={badge.title}
        title={badge.title}
        width={size}
        height={size}
        referrerPolicy="no-referrer"
        draggable={false}
        onError={(event) => {
          event.currentTarget.style.display = "none";
        }}
      />
    ) : null,
  );
}
