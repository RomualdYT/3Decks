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
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="3.2" y="2.7" width="17.6" height="8.2" rx="2.2" stroke="currentColor" strokeWidth="1.55" />
      <rect x="4.6" y="13" width="14.8" height="8.2" rx="2.2" stroke="currentColor" strokeWidth="1.55" />
      <path d="M9 16.2v2.9M7.55 17.65h2.9" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
      <circle cx="15.2" cy="16.7" r=".75" fill="currentColor" /><circle cx="17.1" cy="18.4" r=".75" fill="currentColor" />
      <path d="M9.5 6.8h5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="18.7" cy="4.3" r="2.2" fill={connected ? "#66CB10" : "#718096"} stroke="#09101d" strokeWidth="1" />
    </svg>
  );
}
