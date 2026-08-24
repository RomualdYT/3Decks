"""Adaptateur Windows.

Deux mécanismes sont utilisés :

- un processus PowerShell maintenu ouvert, auquel on envoie des commandes au
  fil de l'eau. Démarrer PowerShell coûte près d'une seconde ; le relancer à
  chaque action rendrait l'interface inutilisable ;
- l'API Win32 via `ctypes` pour les touches multimédia et la fenêtre active,
  car ces appels sont immédiats et ne nécessitent aucun interpréteur.

Aucune dépendance externe n'est requise : la bibliothèque standard suffit.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import threading
import time

from .base import (
    ActionFailed,
    Capabilities,
    MediaInfo,
    Platform,
    SystemSnapshot,
    Unsupported,
)

#: Codes des touches virtuelles multimédia.
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_KEYUP = 0x0002

#: Modificateurs reconnus par `send_hotkey`, avec leur code virtuel.
_MODIFIER_CODES = {
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B,
    "cmd": 0x5B,
    "super": 0x5B,
}

#: Touches spéciales et leur code virtuel.
_SPECIAL_CODES = {
    "return": 0x0D,
    "enter": 0x0D,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "escape": 0x1B,
    "esc": 0x1B,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "printscreen": 0x2C,
}
for _index in range(1, 13):
    _SPECIAL_CODES[f"f{_index}"] = 0x6F + _index


class _PowerShellSession:
    """Processus PowerShell persistant.

    Chaque commande est suivie d'un marqueur de fin, ce qui permet de lire la
    réponse sans ambiguïté sur un flux continu.
    """

    MARKER = "<<<DECK3DS_END>>>"

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def _ensure(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process

        creation_flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            # Évite l'apparition d'une fenêtre de console à chaque démarrage.
            creation_flags = subprocess.CREATE_NO_WINDOW

        try:
            self._process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    "-",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creation_flags,
            )
        except FileNotFoundError as error:
            raise Unsupported("powershell.exe introuvable") from error

        return self._process

    def run(self, script: str, timeout: float = 5.0) -> str:
        with self._lock:
            process = self._ensure()
            assert process.stdin is not None
            assert process.stdout is not None

            try:
                process.stdin.write(f"{script}\n")
                process.stdin.write(f'Write-Output "{self.MARKER}"\n')
                process.stdin.flush()
            except (BrokenPipeError, OSError) as error:
                self.close()
                raise ActionFailed("PowerShell interrompu") from error

            lines: list[str] = []
            deadline = time.monotonic() + timeout

            while True:
                if time.monotonic() > deadline:
                    # Le processus est probablement bloqué : on le recycle pour
                    # que la commande suivante repart d'un état sain.
                    self.close()
                    raise ActionFailed("PowerShell n'a pas repondu")

                line = process.stdout.readline()
                if not line:
                    self.close()
                    raise ActionFailed("PowerShell s'est arrete")

                stripped = line.rstrip("\r\n")
                if stripped == self.MARKER:
                    break
                lines.append(stripped)

            return "\n".join(lines).strip()

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return

        try:
            process.kill()
        except OSError:
            pass


class WindowsPlatform(Platform):
    name = "win32"

    def __init__(self) -> None:
        self._shell = _PowerShellSession()
        self._mic_muted: bool | None = None
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._cpu_count = os.cpu_count() or 1
        # Indique si le module audio a déjà échoué, pour ne pas réessayer en
        # boucle une opération impossible.
        self._audio_broken = False

    # --- Capacités ------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        """Capacités réelles de cet adaptateur, y compris ses manques.

        Quatre familles ne sont pas encore portées : sélection de fenêtre,
        bascule de sortie audio, volume par application et notifications. Les
        déclarer fausses vaut mieux que de laisser l'interface proposer des
        boutons qui resteraient sans effet.

        La pochette est également absente : l'API WinRT n'expose pas d'URL
        d'image, et la conversion repose sur `sips`, propre à macOS.
        """
        return Capabilities(
            volume=True,
            mute=True,
            mic=True,
            app_volume=False,
            audio_output=False,
            media=True,
            media_artwork=False,
            apps=True,
            windows=False,
            hotkey=True,
            open_url=True,
            open_path=True,
            lock=True,
            notifications=False,
            system_stats=True,
        )

    # --- Touches --------------------------------------------------------------

    def _tap(self, code: int) -> None:
        self._user32.keybd_event(code, 0, 0, 0)
        self._user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)

    # --- Volume ---------------------------------------------------------------

    def _audio_script(self, body: str) -> str:
        """Encapsule un accès à l'API audio centrale de Windows.

        L'interface COM `IAudioEndpointVolume` n'est pas exposée à PowerShell :
        on la déclare en C# compilé à la volée. Le type n'est ajouté qu'une fois
        par session grâce au test d'existence.
        """
        return (
            "if (-not ([System.Management.Automation.PSTypeName]"
            "'Deck3DS.Audio').Type) {\n"
            "Add-Type -TypeDefinition @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "namespace Deck3DS {\n"
            '  [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"),'
            " InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
            "  interface IAudioEndpointVolume {\n"
            "    int f(); int g(); int h(); int i();\n"
            "    int SetMasterVolumeLevelScalar(float v, Guid ctx);\n"
            "    int j();\n"
            "    int GetMasterVolumeLevelScalar(out float v);\n"
            "    int k(); int l();\n"
            "    int SetMute([MarshalAs(UnmanagedType.Bool)] bool m, Guid ctx);\n"
            "    int GetMute([MarshalAs(UnmanagedType.Bool)] out bool m);\n"
            "  }\n"
            '  [Guid("D666063F-1587-4E43-81F1-B948E807363F"),'
            " InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
            "  interface IMMDevice {\n"
            "    int Activate(ref Guid id, int clsCtx, IntPtr p,"
            " [MarshalAs(UnmanagedType.IUnknown)] out object i);\n"
            "  }\n"
            '  [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),'
            " InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
            "  interface IMMDeviceEnumerator {\n"
            "    int f();\n"
            "    int GetDefaultAudioEndpoint(int dataFlow, int role,"
            " out IMMDevice dev);\n"
            "  }\n"
            '  [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]\n'
            "  class MMDeviceEnumeratorComObject { }\n"
            "  public class Audio {\n"
            "    static IAudioEndpointVolume Endpoint(int flow) {\n"
            "      IMMDeviceEnumerator e ="
            " (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());\n"
            "      IMMDevice dev;\n"
            "      Marshal.ThrowExceptionForHR("
            "e.GetDefaultAudioEndpoint(flow, 1, out dev));\n"
            "      Guid iid = typeof(IAudioEndpointVolume).GUID;\n"
            "      object o;\n"
            "      Marshal.ThrowExceptionForHR("
            "dev.Activate(ref iid, 23, IntPtr.Zero, out o));\n"
            "      return (IAudioEndpointVolume)o;\n"
            "    }\n"
            "    public static float GetVolume() {\n"
            "      float v; Endpoint(0).GetMasterVolumeLevelScalar(out v);"
            " return v * 100f;\n"
            "    }\n"
            "    public static void SetVolume(float v) {\n"
            "      Endpoint(0).SetMasterVolumeLevelScalar(v / 100f, Guid.Empty);\n"
            "    }\n"
            "    public static bool GetMute() {\n"
            "      bool m; Endpoint(0).GetMute(out m); return m;\n"
            "    }\n"
            "    public static void SetMute(bool m) {\n"
            "      Endpoint(0).SetMute(m, Guid.Empty);\n"
            "    }\n"
            "    public static bool GetMicMute() {\n"
            "      bool m; Endpoint(1).GetMute(out m); return m;\n"
            "    }\n"
            "    public static void SetMicMute(bool m) {\n"
            "      Endpoint(1).SetMute(m, Guid.Empty);\n"
            "    }\n"
            "  }\n"
            "}\n"
            "'@\n"
            "}\n" + body
        )

    def get_volume(self) -> int | None:
        if self._audio_broken:
            return None
        try:
            raw = self._shell.run(
                self._audio_script("[Deck3DS.Audio]::GetVolume()"), timeout=12.0
            )
        except (Unsupported, ActionFailed):
            self._audio_broken = True
            return None

        match = re.search(r"[\d.,]+", raw)
        if not match:
            return None
        try:
            return max(0, min(100, int(round(float(match.group().replace(",", "."))))))
        except ValueError:
            return None

    def set_volume(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        self._shell.run(
            self._audio_script(f"[Deck3DS.Audio]::SetVolume({value})"), timeout=12.0
        )

    def is_muted(self) -> bool | None:
        if self._audio_broken:
            return None
        try:
            raw = self._shell.run(
                self._audio_script("[Deck3DS.Audio]::GetMute()"), timeout=12.0
            )
        except (Unsupported, ActionFailed):
            return None
        return raw.strip().lower() == "true"

    def set_muted(self, muted: bool) -> None:
        flag = "$true" if muted else "$false"
        try:
            self._shell.run(
                self._audio_script(f"[Deck3DS.Audio]::SetMute({flag})"), timeout=12.0
            )
        except (Unsupported, ActionFailed):
            # Repli sur la touche multimédia, qui bascule sans permettre de
            # fixer un état précis.
            self._tap(VK_VOLUME_MUTE)

    # --- Microphone -----------------------------------------------------------

    def is_mic_muted(self) -> bool | None:
        if self._audio_broken:
            return self._mic_muted
        try:
            raw = self._shell.run(
                self._audio_script("[Deck3DS.Audio]::GetMicMute()"), timeout=12.0
            )
        except (Unsupported, ActionFailed):
            return self._mic_muted

        if raw.strip().lower() in {"true", "false"}:
            return raw.strip().lower() == "true"
        return self._mic_muted

    def set_mic_muted(self, muted: bool) -> None:
        flag = "$true" if muted else "$false"
        self._shell.run(
            self._audio_script(f"[Deck3DS.Audio]::SetMicMute({flag})"), timeout=12.0
        )
        self._mic_muted = muted

    # --- Média ----------------------------------------------------------------

    def get_media(self) -> MediaInfo | None:
        """Média courant via les contrôles de transport système.

        L'API `GlobalSystemMediaTransportControlsSessionManager` expose ce que
        joue n'importe quelle application compatible, navigateurs inclus. Elle
        n'est disponible qu'à partir de Windows 10.
        """
        script = (
            "try {\n"
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime "
            "-ErrorAction Stop\n"
            "$T = [Windows.Media.Control."
            "GlobalSystemMediaTransportControlsSessionManager,"
            "Windows.Media.Control,ContentType=WindowsRuntime]\n"
            "$op = $T::RequestAsync()\n"
            "$m = ([System.WindowsRuntimeSystemExtensions].GetMethods() | "
            "Where-Object { $_.Name -eq 'GetAwaiter' -and "
            "$_.GetParameters().Count -eq 1 } | Select-Object -First 1)."
            "MakeGenericMethod([Windows.Media.Control."
            "GlobalSystemMediaTransportControlsSessionManager,"
            "Windows.Media.Control,ContentType=WindowsRuntime])\n"
            "$mgr = $m.Invoke($null, @($op)).GetResult()\n"
            "$s = $mgr.GetCurrentSession()\n"
            "if ($s) {\n"
            "  $pop = $s.TryGetMediaPropertiesAsync()\n"
            "  $pm = ([System.WindowsRuntimeSystemExtensions].GetMethods() | "
            "Where-Object { $_.Name -eq 'GetAwaiter' -and "
            "$_.GetParameters().Count -eq 1 } | Select-Object -First 1)."
            "MakeGenericMethod([Windows.Media.Control."
            "GlobalSystemMediaTransportControlsSessionMediaProperties,"
            "Windows.Media.Control,ContentType=WindowsRuntime])\n"
            "  $p = $pm.Invoke($null, @($pop)).GetResult()\n"
            "  $st = $s.GetPlaybackInfo().PlaybackStatus\n"
            "  Write-Output ("
            "$p.Title + '|' + $p.Artist + '|' + $s.SourceAppUserModelId "
            "+ '|' + $st)\n"
            "}\n"
            "} catch { }"
        )

        try:
            raw = self._shell.run(script, timeout=10.0)
        except (Unsupported, ActionFailed):
            return None

        if not raw or "|" not in raw:
            return None

        # La dernière ligne utile évite les avertissements éventuels.
        line = [item for item in raw.splitlines() if "|" in item]
        if not line:
            return None

        fields = line[-1].split("|")
        if len(fields) < 4:
            return None

        title = fields[0].strip()
        if not title:
            return None

        app = fields[2].strip()
        # L'identifiant de paquet est illisible : on garde une forme courte.
        if "!" in app:
            app = app.split("!")[0]
        if "." in app and len(app) > 24:
            app = app.split(".")[-1]

        return MediaInfo(
            title=title,
            artist=fields[1].strip(),
            app=app,
            playing=fields[3].strip() == "Playing",
        )

    def media_play_pause(self) -> None:
        self._tap(VK_MEDIA_PLAY_PAUSE)

    def media_next(self) -> None:
        self._tap(VK_MEDIA_NEXT)

    def media_previous(self) -> None:
        self._tap(VK_MEDIA_PREV)

    # --- Applications ---------------------------------------------------------

    def get_active_app(self) -> str:
        handle = self._user32.GetForegroundWindow()
        if not handle:
            return ""

        pid = ctypes.c_ulong(0)
        self._user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == 0:
            return ""

        try:
            raw = self._shell.run(
                f"(Get-Process -Id {pid.value} -ErrorAction SilentlyContinue)"
                ".ProcessName",
                timeout=4.0,
            )
        except (Unsupported, ActionFailed):
            return ""

        return raw.strip().splitlines()[0].strip() if raw.strip() else ""

    def list_apps(self) -> list[str]:
        try:
            raw = self._shell.run(
                "Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | "
                "Select-Object -ExpandProperty ProcessName -Unique",
                timeout=6.0,
            )
        except (Unsupported, ActionFailed):
            return []

        return [line.strip() for line in raw.splitlines() if line.strip()][:16]

    def launch_app(self, target: str) -> None:
        self.spawn(["cmd", "/c", "start", "", target])

    def quit_app(self, target: str) -> None:
        name = target.rsplit(".", 1)[0] if target.lower().endswith(".exe") else target
        # `-replace` neutralise les caractères susceptibles d'altérer la
        # commande PowerShell.
        safe = re.sub(r"[^A-Za-z0-9_.\- ]", "", name)
        if not safe:
            raise ActionFailed("nom d'application invalide")

        self._shell.run(
            f"Get-Process -Name '{safe}' -ErrorAction SilentlyContinue | "
            "ForEach-Object { $_.CloseMainWindow() | Out-Null }",
            timeout=6.0,
        )

    # --- Système --------------------------------------------------------------

    def open_url(self, url: str) -> None:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            url = f"https://{url}"
        self.spawn(["cmd", "/c", "start", "", url])

    def open_path(self, path: str) -> None:
        self.spawn(["explorer.exe", path])

    def send_hotkey(self, keys: str) -> None:
        parts = [part.strip().lower() for part in keys.split("+") if part.strip()]
        if not parts:
            raise ActionFailed("combinaison vide")

        modifiers = [_MODIFIER_CODES[part] for part in parts if part in _MODIFIER_CODES]
        remaining = [part for part in parts if part not in _MODIFIER_CODES]

        if len(remaining) != 1:
            raise ActionFailed(f"combinaison invalide: {keys}")

        key = remaining[0]
        if key in _SPECIAL_CODES:
            code = _SPECIAL_CODES[key]
        elif len(key) == 1:
            code = ord(key.upper())
        else:
            raise ActionFailed(f"touche inconnue: {key}")

        for modifier in modifiers:
            self._user32.keybd_event(modifier, 0, 0, 0)
        self._tap(code)
        for modifier in reversed(modifiers):
            self._user32.keybd_event(modifier, 0, KEYEVENTF_KEYUP, 0)

    def lock_session(self) -> None:
        ctypes.WinDLL("user32").LockWorkStation()

    def get_cpu(self) -> int | None:
        try:
            raw = self._shell.run(
                "(Get-CimInstance Win32_Processor | "
                "Measure-Object -Property LoadPercentage -Average).Average",
                timeout=8.0,
            )
        except (Unsupported, ActionFailed):
            return None

        match = re.search(r"\d+", raw)
        return max(0, min(100, int(match.group()))) if match else None

    def get_memory(self) -> int | None:
        try:
            raw = self._shell.run(
                "$o = Get-CimInstance Win32_OperatingSystem; "
                "[int](100 - ($o.FreePhysicalMemory / "
                "$o.TotalVisibleMemorySize * 100))",
                timeout=8.0,
            )
        except (Unsupported, ActionFailed):
            return None

        match = re.search(r"\d+", raw)
        return max(0, min(100, int(match.group()))) if match else None

    def snapshot(self) -> SystemSnapshot:
        snapshot = super().snapshot()
        # Sur Windows, l'état du micro provient de l'API audio ; s'il est resté
        # inconnu, on complète avec le suivi local.
        if snapshot.mic_muted is None:
            snapshot.mic_muted = self._mic_muted
        return snapshot

    def close(self) -> None:
        self._shell.close()
