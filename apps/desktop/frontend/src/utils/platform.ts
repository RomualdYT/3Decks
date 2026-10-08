/** Display labels only: protocol identifiers remain unchanged. */
export function platformLabel(platform?: string): string {
  switch (platform) {
    case "darwin": case "macos": return "macOS";
    case "win32": case "windows": return "Windows";
    case "linux": return "Linux";
    default: return platform || "3Decks";
  }
}
