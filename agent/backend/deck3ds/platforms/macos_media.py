"""Lecteurs multimédia macOS : Spotify et Apple Music."""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from .base import ActionFailed, MediaInfo, Unsupported

SCRIPT_TIMEOUT = 2.5
FAILURE_RETRY_DELAY = 5.0
MEDIA_PLAYERS = ("Spotify", "Music")
PLAYER_FEATURE = {"Spotify": "spotify", "Music": "apple_music"}
PLAYER_LABEL = {"Spotify": "Spotify", "Music": "Apple Music"}

KEY_PREVIOUS = 98
KEY_PLAY_PAUSE = 100
KEY_NEXT = 101


def parse_number(text: str) -> float | None:
    """Lit un nombre AppleScript, quelle que soit la locale du Mac."""
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _music_artwork_script() -> str:
    """AppleScript qui exporte la pochette Apple Music dans le dossier temporaire."""
    return (
        "  try\n"
        "    set deckArtwork to artwork 1 of deckTrack\n"
        "    set deckArtworkId to persistent ID of deckTrack\n"
        "    set deckArtPath to (POSIX path of (path to temporary items)) & "
        '"3decks-music-" & deckArtworkId & ".art"\n'
        "    set deckArtFile to open for access POSIX file deckArtPath "
        "with write permission\n"
        "    set eof deckArtFile to 0\n"
        "    write (raw data of deckArtwork) to deckArtFile starting at 0\n"
        "    close access deckArtFile\n"
        '    set deckArt to "file://" & deckArtPath\n'
        "  on error\n"
        "    try\n"
        "      close access deckArtFile\n"
        "    end try\n"
        "  end try\n"
    )


def build_player_script(player: str) -> str:
    """Une requête unique par lecteur, garde de présence comprise."""
    artwork = (
        "  try\n"
        "    set deckArt to artwork url of deckTrack\n"
        "  end try\n"
        if player == "Spotify"
        else _music_artwork_script()
    )
    return (
        f'if application "{player}" is not running then return ""\n'
        f'tell application "{player}"\n'
        "  set deckState to player state as text\n"
        '  set deckTitle to ""\n'
        '  set deckArtist to ""\n'
        '  set deckAlbum to ""\n'
        '  set deckArt to ""\n'
        '  set deckPos to ""\n'
        '  set deckDur to ""\n'
        '  set deckVol to ""\n'
        "  try\n"
        "    set deckTrack to current track\n"
        "    set deckTitle to name of deckTrack\n"
        "    set deckArtist to artist of deckTrack\n"
        "    set deckAlbum to album of deckTrack\n"
        "    set deckDur to (duration of deckTrack) as text\n"
        "  end try\n"
        f"{artwork}"
        "  try\n"
        "    set deckPos to (player position) as text\n"
        "  end try\n"
        "  try\n"
        "    set deckVol to (sound volume) as text\n"
        "  end try\n"
        '  return deckState & "\\n" & deckTitle & "\\n" & deckArtist'
        ' & "\\n" & deckAlbum & "\\n" & deckArt & "\\n" & deckPos'
        ' & "\\n" & deckDur & "\\n" & deckVol\n'
        "end tell"
    )


class MacMediaProvider:
    """Collecte et commandes média, isolées de l'adaptateur système."""

    def __init__(
        self,
        run: Callable[..., str],
        run_quiet: Callable[..., str | None],
        feature_enabled: Callable[[str], bool],
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._run = run
        self._run_quiet = run_quiet
        self._feature_enabled = feature_enabled
        self._clock = clock
        self.preferred_player = ""
        self.retry_after: dict[str, float] = {}
        self.volume: int | None = None

    def _players_to_try(self) -> list[str]:
        now = self._clock()
        order = [
            player
            for player in MEDIA_PLAYERS
            if self._feature_enabled(PLAYER_FEATURE[player])
            and self.retry_after.get(player, 0.0) <= now
        ]
        if self.preferred_player in order:
            order.remove(self.preferred_player)
            order.insert(0, self.preferred_player)
        return order

    def get_media(self) -> MediaInfo | None:
        """Retourne le premier lecteur actif en un appel AppleScript par source."""
        for player in self._players_to_try():
            raw = self._run_quiet(build_player_script(player))
            if raw is None:
                # Un refus d'automatisation peut être temporaire : macOS
                # affiche souvent la demande d'autorisation pendant la
                # première collecte. Une liste noire permanente obligeait
                # alors à redémarrer l'agent après avoir accepté. Un court
                # délai évite de répéter une erreur chaque seconde tout en
                # reprenant automatiquement dès que l'accès est accordé.
                self.retry_after[player] = self._clock() + FAILURE_RETRY_DELAY
                continue

            self.retry_after.pop(player, None)

            lines = raw.split("\n")
            if not lines or not lines[0]:
                continue

            def field(index: int) -> str:
                return lines[index].strip() if len(lines) > index else ""

            title = field(1)
            if not title:
                continue

            duration = parse_number(field(6))
            if duration is not None and duration > 10000:
                duration /= 1000.0

            volume = parse_number(field(7))
            self.volume = None if volume is None else max(0, min(100, int(volume)))
            self.preferred_player = player

            return MediaInfo(
                title=title,
                artist=field(2),
                app=PLAYER_LABEL[player],
                playing=field(0).lower() == "playing",
                album=field(3),
                art_url=field(4),
                position=parse_number(field(5)),
                duration=duration,
            )

        self.volume = None
        return None

    def _volume_player(self) -> str | None:
        preferred = self.preferred_player
        if preferred in self._players_to_try():
            return preferred
        for player in self._players_to_try():
            if self._run_quiet(f'application "{player}" is running') == "true":
                return player
        return None

    def get_volume(self) -> int | None:
        player = self._volume_player()
        if player is None:
            return None
        raw = self._run_quiet(f'tell application "{player}" to return sound volume')
        if raw is None or not raw.lstrip("-").isdigit():
            return None
        return max(0, min(100, int(raw)))

    def set_volume(self, value: int) -> None:
        player = self._volume_player()
        if player is None:
            raise Unsupported("Aucun lecteur compatible n'est lancé")
        value = max(0, min(100, int(value)))
        self._run(f'tell application "{player}" to set sound volume to {value}')
        self.volume = value

    def _media_key(self, key_code: int) -> None:
        self._run(f'tell application "System Events" to key code {key_code}')

    def command(self, command: str, key_code: int) -> None:
        player = self._volume_player()
        if player is not None:
            try:
                self._run(f'tell application "{player}" to {command}')
                return
            except (Unsupported, ActionFailed):
                pass
        self._media_key(key_code)

    def play_pause(self) -> None:
        self.command("playpause", KEY_PLAY_PAUSE)

    def next(self) -> None:
        self.command("next track", KEY_NEXT)

    def previous(self) -> None:
        self.command("previous track", KEY_PREVIOUS)
