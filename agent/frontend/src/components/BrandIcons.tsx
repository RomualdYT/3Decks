export function SpotifyIcon({ size = 22 }: { size?: number }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="11" fill="#1ED760" />
      <path d="M6.4 9.2c3.9-1.1 8.3-.7 11.4 1" stroke="#07130b" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M7.2 12.3c3.2-.8 6.9-.5 9.6.8" stroke="#07130b" strokeWidth="1.55" strokeLinecap="round" />
      <path d="M8 15.2c2.7-.5 5.6-.25 7.8.8" stroke="#07130b" strokeWidth="1.35" strokeLinecap="round" />
    </svg>
  );
}

export function AppleMusicIcon({ size = 22 }: { size?: number }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <defs><linearGradient id="apple-music-gradient" x1="4" y1="2" x2="20" y2="22"><stop stopColor="#fa5c74" /><stop offset="1" stopColor="#a73cff" /></linearGradient></defs>
      <rect x="1" y="1" width="22" height="22" rx="5.5" fill="url(#apple-music-gradient)" />
      <path d="M16.9 6.2v9.2a2.55 2.55 0 1 1-1.3-2.22V8.55l-5.75 1.12v7.05a2.55 2.55 0 1 1-1.3-2.22V8.35c0-.55.34-.9.9-1l6.45-1.25c.48-.1 1 .05 1 .1Z" fill="white" />
    </svg>
  );
}

export function ConsoleConnectionIcon({ connected, size = 21 }: { connected: boolean; size?: number }) {
  return (
    <svg aria-hidden="true" data-connected={connected} width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="3.25" y="2.2" width="17.5" height="8.8" rx="2.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="4.25" y="12.15" width="15.5" height="9.65" rx="2.8" stroke="currentColor" strokeWidth="1.6" />
      <rect x="6.15" y="4.1" width="11.7" height="4.95" rx="1.15" fill="currentColor" opacity=".13" />
      <path d="M7.65 16.95h3.9M9.6 15v3.9" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
      <circle cx="15.25" cy="16.25" r=".85" fill="currentColor" />
      <circle cx="17.45" cy="18.1" r=".85" fill="currentColor" />
    </svg>
  );
}
