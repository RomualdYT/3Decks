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

import base64
import ctypes
import json
import os
import queue
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from ..config import MAX_LIST_ENTRIES
from ..keys import MODIFIER_BY_NAME, InvalidHotkey, parse_hotkey
from ..messages import msg
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
SW_RESTORE = 9
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

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
                encoding="utf-8",
                errors="replace",
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
                # `powershell -Command -` interprète l'entrée ligne par ligne.
                # Un script contenant un here-string (notamment le helper C#
                # audio) serait donc exécuté avant d'être complet. On transmet
                # le bloc en base64 pour qu'une seule ligne atomique soit lue.
                encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
                process.stdin.write(
                    "$deck3dsSource=[Text.Encoding]::UTF8.GetString("
                    f"[Convert]::FromBase64String('{encoded}'));"
                    "& ([ScriptBlock]::Create($deck3dsSource));"
                    f'Write-Output "{self.MARKER}"\n'
                )
                process.stdin.flush()
            except (BrokenPipeError, OSError) as error:
                self.close()
                raise ActionFailed("PowerShell interrompu") from error

            result: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

            def read_response() -> None:
                lines: list[str] = []
                try:
                    while True:
                        line = process.stdout.readline()
                        if not line:
                            raise ActionFailed("PowerShell s'est arrete")
                        stripped = line.rstrip("\r\n")
                        if stripped == self.MARKER:
                            result.put((True, "\n".join(lines).strip()))
                            return
                        lines.append(stripped)
                except BaseException as error:
                    result.put((False, error))

            # readline() est bloquant sous Windows. Un thread permet au délai
            # d'expirer même quand PowerShell ou une API COM ne répond plus.
            threading.Thread(target=read_response, daemon=True).start()
            try:
                succeeded, value = result.get(timeout=timeout)
            except queue.Empty as error:
                self.close()
                raise ActionFailed("PowerShell n'a pas repondu") from error

            if not succeeded:
                self.close()
                assert isinstance(value, BaseException)
                raise value
            assert isinstance(value, str)
            return value

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
        self._user32.GetForegroundWindow.restype = ctypes.c_void_p
        self._user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        self._user32.GetWindowTextW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_int,
        ]
        self._user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        self._user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        # Traduit un caractère en position de touche sur la disposition
        # réellement installée : indispensable sur un clavier AZERTY.
        self._user32.VkKeyScanW.argtypes = [ctypes.c_wchar]
        self._user32.VkKeyScanW.restype = ctypes.c_short
        self._cpu_count = os.cpu_count() or 1
        # Indique si le module audio a déjà échoué, pour ne pas réessayer en
        # boucle une opération impossible.
        self._audio_broken = False
        self._media_key = ""
        self._media_art_url = ""
        self._media_error = ""

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
            audio_output=True,
            media=True,
            media_artwork=True,
            apps=True,
            windows=True,
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
        return r'''
if (-not ([System.Management.Automation.PSTypeName]'Deck3DS.Audio').Type) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Deck3DS {
  [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IAudioEndpointVolume {
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float v, Guid ctx);
    int j();
    int GetMasterVolumeLevelScalar(out float v);
    int k(); int l();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool m, Guid ctx);
    int GetMute([MarshalAs(UnmanagedType.Bool)] out bool m);
  }
  [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDevice {
    int Activate(ref Guid id, int clsCtx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object i);
    int OpenPropertyStore(int access, out IntPtr properties);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
  }
  [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDeviceEnumerator {
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice dev);
  }
  [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
  class MMDeviceEnumeratorComObject { }
  public class Audio {
    static IAudioEndpointVolume Endpoint(int flow) {
      IMMDeviceEnumerator e = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
      IMMDevice dev;
      Marshal.ThrowExceptionForHR(e.GetDefaultAudioEndpoint(flow, 1, out dev));
      Guid iid = typeof(IAudioEndpointVolume).GUID;
      object o;
      Marshal.ThrowExceptionForHR(dev.Activate(ref iid, 23, IntPtr.Zero, out o));
      return (IAudioEndpointVolume)o;
    }
    public static float GetVolume() {
      float v; Endpoint(0).GetMasterVolumeLevelScalar(out v); return v * 100f;
    }
    public static void SetVolume(float v) {
      Endpoint(0).SetMasterVolumeLevelScalar(v / 100f, Guid.Empty);
    }
    public static bool GetMute() {
      bool m; Endpoint(0).GetMute(out m); return m;
    }
    public static void SetMute(bool m) {
      Endpoint(0).SetMute(m, Guid.Empty);
    }
    public static bool GetMicMute() {
      bool m; Endpoint(1).GetMute(out m); return m;
    }
    public static void SetMicMute(bool m) {
      Endpoint(1).SetMute(m, Guid.Empty);
    }
    public static string GetDefaultOutputId() {
      IMMDeviceEnumerator e = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
      IMMDevice dev; Marshal.ThrowExceptionForHR(e.GetDefaultAudioEndpoint(0, 1, out dev));
      string id; Marshal.ThrowExceptionForHR(dev.GetId(out id)); return id;
    }
  }
}
'@
}
''' + body

    def _device_script(self, body: str) -> str:
        """Interfaces COM d'énumération et de sélection des sorties audio."""
        return r'''
if (-not ([System.Management.Automation.PSTypeName]'Deck3DS.AudioDevices').Type) {
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
namespace Deck3DS {
  [StructLayout(LayoutKind.Sequential)]
  struct PropertyKey { public Guid formatId; public int propertyId; }
  [StructLayout(LayoutKind.Explicit)]
  struct PropertyVariant {
    [FieldOffset(0)] public ushort variantType;
    [FieldOffset(8)] public IntPtr pointerValue;
    public string Text() { return Marshal.PtrToStringUni(pointerValue) ?? ""; }
  }
  [ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-C0A1CE7191C3"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDeviceCollection {
    [PreserveSig] int GetCount(out uint count);
    [PreserveSig] int Item(uint index, out IMMDevice device);
  }
  [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IPropertyStore {
    [PreserveSig] int GetCount(out uint count);
    [PreserveSig] int GetAt(uint index, out PropertyKey key);
    [PreserveSig] int GetValue(ref PropertyKey key, out PropertyVariant value);
    int SetValue(ref PropertyKey key, ref PropertyVariant value);
    int Commit();
  }
  [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDevice {
    [PreserveSig] int Activate(ref Guid id, int clsCtx, IntPtr parameters, [MarshalAs(UnmanagedType.IUnknown)] out object result);
    [PreserveSig] int OpenPropertyStore(int access, out IPropertyStore properties);
    [PreserveSig] int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    [PreserveSig] int GetState(out int state);
  }
  [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDeviceEnumerator {
    [PreserveSig] int EnumAudioEndpoints(int flow, int mask, out IMMDeviceCollection devices);
    [PreserveSig] int GetDefaultAudioEndpoint(int flow, int role, out IMMDevice device);
    [PreserveSig] int GetDevice(string id, out IMMDevice device);
    int RegisterEndpointNotificationCallback(IntPtr client);
    int UnregisterEndpointNotificationCallback(IntPtr client);
  }
  [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
  class MMDeviceEnumeratorComObject { }
  enum ERole { Console = 0, Multimedia = 1, Communications = 2 }
  [ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IPolicyConfig {
    int GetMixFormat(string id, IntPtr format);
    int GetDeviceFormat(string id, int @default, IntPtr format);
    int ResetDeviceFormat(string id);
    int SetDeviceFormat(string id, IntPtr endpoint, IntPtr mix);
    int GetProcessingPeriod(string id, int @default, IntPtr period, IntPtr minimum);
    int SetProcessingPeriod(string id, IntPtr period);
    int GetShareMode(string id, IntPtr mode);
    int SetShareMode(string id, IntPtr mode);
    int GetPropertyValue(string id, IntPtr key, IntPtr value);
    int SetPropertyValue(string id, IntPtr key, IntPtr value);
    int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)] string id, ERole role);
    int SetEndpointVisibility(string id, int visible);
  }
  [ComImport, Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9")]
  class PolicyConfigClient { }
  public class AudioDevices {
    static IMMDeviceEnumerator Enumerator() { return (IMMDeviceEnumerator)new MMDeviceEnumeratorComObject(); }
    static string Name(IMMDevice device) {
      IPropertyStore store; Marshal.ThrowExceptionForHR(device.OpenPropertyStore(0, out store));
      PropertyKey key = new PropertyKey { formatId = new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"), propertyId = 14 };
      PropertyVariant value; Marshal.ThrowExceptionForHR(store.GetValue(ref key, out value));
      return value.Text();
    }
    public static string[] Outputs() {
      IMMDeviceCollection collection; Marshal.ThrowExceptionForHR(Enumerator().EnumAudioEndpoints(0, 1, out collection));
      uint count; collection.GetCount(out count); var result = new List<string>();
      for (uint i = 0; i < count; i++) { IMMDevice device; collection.Item(i, out device); string id; device.GetId(out id); result.Add(id + "\t" + Name(device)); }
      return result.ToArray();
    }
    public static string DefaultId() { IMMDevice device; Enumerator().GetDefaultAudioEndpoint(0, 1, out device); string id; device.GetId(out id); return id; }
    public static void SetDefault(string id) { var policy = (IPolicyConfig)new PolicyConfigClient(); for (int role = 0; role < 3; role++) Marshal.ThrowExceptionForHR(policy.SetDefaultEndpoint(id, (ERole)role)); }
  }
}
'@
}
''' + body

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

    # --- Sorties audio -------------------------------------------------------

    def _audio_devices(self) -> list[tuple[str, str]]:
        script = (
            "$root='HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\MMDevices\\Audio\\Render'; "
            "Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object { "
            "$device=Get-ItemProperty $_.PSPath; if ($device.DeviceState -eq 1) { "
            "$properties=Get-ItemProperty ($_.PSPath+'\\Properties'); "
            "$name=$properties.'{a45c254e-df1c-4efd-8020-67d146a850e0},2'; "
            "if ($name) { Write-Output ('{0.0.0.00000000}.'+$_.PSChildName + \"`t\" + $name) } } }"
        )
        try:
            raw = self._shell.run(script, timeout=8.0)
        except (Unsupported, ActionFailed):
            return []
        devices: list[tuple[str, str]] = []
        for line in raw.splitlines():
            if "\t" not in line:
                continue
            identifier, name = line.split("\t", 1)
            if identifier.strip() and name.strip():
                devices.append((identifier.strip(), name.strip()))
        return devices

    def get_audio_output(self) -> str:
        devices = self._audio_devices()
        if not devices:
            return ""
        try:
            current = self._shell.run(
                self._audio_script("[Deck3DS.Audio]::GetDefaultOutputId()"),
                timeout=12.0,
            ).strip()
        except (Unsupported, ActionFailed):
            return ""
        return next((name for identifier, name in devices if identifier == current), "")

    def list_audio_outputs(self) -> list[str]:
        return [name for _, name in self._audio_devices()]

    def select_audio_output(self, needle: str) -> str:
        match = next(
            (
                (identifier, name)
                for identifier, name in self._audio_devices()
                if needle.casefold() in name.casefold()
            ),
            None,
        )
        if match is None:
            raise ActionFailed(msg("output_not_found", name=needle))
        identifier, name = match
        escaped = identifier.replace("'", "''")
        self._shell.run(
            self._device_script(f"[Deck3DS.AudioDevices]::SetDefault('{escaped}')"),
            timeout=12.0,
        )
        return name

    def cycle_audio_output(self) -> str:
        devices = self._audio_devices()
        if len(devices) < 2:
            raise ActionFailed(msg("single_output"))
        current = self.get_audio_output()
        index = next(
            (position for position, (_, name) in enumerate(devices) if name == current),
            -1,
        )
        identifier, name = devices[(index + 1) % len(devices)]
        escaped = identifier.replace("'", "''")
        self._shell.run(
            self._device_script(f"[Deck3DS.AudioDevices]::SetDefault('{escaped}')"),
            timeout=12.0,
        )
        return name

    # --- Média ----------------------------------------------------------------

    def get_media(self) -> MediaInfo | None:
        """Média courant via les contrôles de transport système.

        L'API `GlobalSystemMediaTransportControlsSessionManager` expose ce que
        joue n'importe quelle application compatible, navigateurs inclus. Elle
        n'est disponible qu'à partir de Windows 10.
        """
        # Les API WinRT sont asynchrones et PowerShell ne sait pas les attendre
        # directement : il faut retrouver la surcharge générique de `AsTask` par
        # réflexion, puis la spécialiser pour chaque type de résultat. Le motif
        # était recopié trois fois ; une fonction locale le porte désormais une
        # seule fois, ce qui évite qu'une correction n'en oublie une copie.
        script = r'''
try {
Add-Type -AssemblyName System.Runtime.WindowsRuntime -ErrorAction Stop
function Wait-Deck3DSAsync($operation, $resultType) {
  $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
  $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
  $task.Wait()
  return $task.Result
}
$sessionType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
$mgr = Wait-Deck3DSAsync ($sessionType::RequestAsync()) $sessionType
$s = $mgr.GetCurrentSession()
if ($s) {
  $propertiesType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties,Windows.Media.Control,ContentType=WindowsRuntime]
  $p = Wait-Deck3DSAsync ($s.TryGetMediaPropertiesAsync()) $propertiesType
  $st = $s.GetPlaybackInfo().PlaybackStatus
  $tl = $s.GetTimelineProperties()
  $mediaKey = $p.Title + '|' + $p.Artist + '|' + $p.AlbumTitle
  $art = ''
  if ($p.Thumbnail -and $global:Deck3DSArtKey -ne $mediaKey) {
    $streamType = [Windows.Storage.Streams.IRandomAccessStreamWithContentType,Windows.Storage.Streams,ContentType=WindowsRuntime]
    $stream = Wait-Deck3DSAsync ($p.Thumbnail.OpenReadAsync()) $streamType
    $asStream = [System.IO.WindowsRuntimeStreamExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsStreamForRead' -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
    $net = $asStream.Invoke($null, @($stream))
    $memory = New-Object System.IO.MemoryStream
    $net.CopyTo($memory)
    $art = [Convert]::ToBase64String($memory.ToArray())
    $global:Deck3DSArtKey = $mediaKey
  }
  [PSCustomObject]@{title=$p.Title; artist=$p.Artist; album=$p.AlbumTitle; app=$s.SourceAppUserModelId; playing=($st -eq 'Playing'); position=[math]::Max(0,$tl.Position.TotalSeconds); duration=[math]::Max(0,($tl.EndTime-$tl.StartTime).TotalSeconds); key=$mediaKey; art=$art} | ConvertTo-Json -Compress
}
} catch { Write-Output ('DECK3DS_ERROR ' + $_.Exception.ToString()) }
'''

        try:
            raw = self._shell.run(script, timeout=10.0)
        except (Unsupported, ActionFailed):
            return None

        if not raw:
            return None

        data = None
        for line in reversed(raw.splitlines()):
            try:
                candidate = json.loads(line)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(candidate, dict):
                data = candidate
                break
        if data is None:
            self._media_error = raw
            return None
        self._media_error = ""

        title = str(data.get("title") or "").strip()
        if not title:
            return None

        app = str(data.get("app") or "").strip()
        # L'identifiant de paquet est illisible : on garde une forme courte.
        if "!" in app:
            app = app.split("!")[0]
        if "." in app and len(app) > 24:
            app = app.split(".")[-1]

        media_key = str(data.get("key") or f"{title}|{data.get('artist', '')}")
        encoded_art = str(data.get("art") or "")
        if media_key != self._media_key:
            self._media_key = media_key
            self._media_art_url = ""
        if encoded_art:
            try:
                image = base64.b64decode(encoded_art, validate=True)
                art_path = Path(tempfile.gettempdir()) / "deck3ds-winrt-artwork.img"
                art_path.write_bytes(image)
                self._media_art_url = art_path.as_uri()
            except (OSError, ValueError):
                self._media_art_url = ""

        return MediaInfo(
            title=title,
            artist=str(data.get("artist") or "").strip(),
            app=app,
            playing=bool(data.get("playing")),
            album=str(data.get("album") or "").strip(),
            art_url=self._media_art_url,
            position=float(data.get("position") or 0),
            duration=float(data.get("duration") or 0) or None,
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

    def _window_records(self) -> list[tuple[int, str, str]]:
        """Fenêtres visibles avec leur handle, exécutable et titre."""
        records: list[tuple[int, str, str]] = []
        user32 = self._user32
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )

        def visit(handle: int, _parameter: int) -> bool:
            if not user32.IsWindowVisible(handle):
                return True
            length = user32.GetWindowTextLengthW(handle)
            if length <= 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, title_buffer, length + 1)
            title = title_buffer.value.strip()
            if not title:
                return True

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
            process = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
            )
            app = ""
            if process:
                try:
                    size = ctypes.c_ulong(32768)
                    path_buffer = ctypes.create_unicode_buffer(size.value)
                    if kernel32.QueryFullProcessImageNameW(
                        process, 0, path_buffer, ctypes.byref(size)
                    ):
                        app = os.path.splitext(os.path.basename(path_buffer.value))[0]
                finally:
                    kernel32.CloseHandle(process)
            if app:
                records.append((int(handle), app, title))
            return True

        callback = callback_type(visit)
        user32.EnumWindows(callback, 0)
        return records

    def list_windows(self) -> list[tuple[str, str]]:
        return [(app, title) for _, app, title in self._window_records()][
            :MAX_LIST_ENTRIES
        ]

    def focus_window(self, app: str, title: str) -> str:
        app_needle = app.casefold().removesuffix(".exe")
        title_needle = title.casefold()
        match: tuple[int, str, str] | None = None
        for record in self._window_records():
            _, candidate_app, candidate_title = record
            if app_needle and app_needle not in candidate_app.casefold():
                continue
            if title_needle and title_needle not in candidate_title.casefold():
                continue
            match = record
            break
        if match is None:
            raise ActionFailed(msg("window_not_found", name=title or app))

        handle, candidate_app, candidate_title = match
        self._user32.ShowWindow(handle, SW_RESTORE)
        if not self._user32.SetForegroundWindow(handle):
            self._tap(0x12)
            self._user32.SetForegroundWindow(handle)
        return candidate_title or candidate_app

    def launch_app(self, target: str) -> None:
        aliases = {
            "safari": ["cmd", "/c", "start", "", "https://www.google.com"],
            "browser": ["cmd", "/c", "start", "", "https://www.google.com"],
            "terminal": ["cmd", "/c", "start", "", "wt.exe"],
            "visual studio code": ["cmd", "/c", "start", "", "code"],
            "mail": ["cmd", "/c", "start", "", "mailto:"],
            "messages": ["cmd", "/c", "start", "", "ms-chat:"],
        }
        command = aliases.get(
            target.casefold(), ["cmd", "/c", "start", "", target]
        )
        self.spawn(command)

    def quit_app(self, target: str) -> None:
        name = target.rsplit(".", 1)[0] if target.lower().endswith(".exe") else target
        # `-replace` neutralise les caractères susceptibles d'altérer la
        # commande PowerShell.
        safe = re.sub(r"[^A-Za-z0-9_.\- ]", "", name)
        if not safe:
            raise ActionFailed(msg("invalid_app"))

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
        self.spawn(["explorer.exe", os.path.expanduser(path)])

    def _character_code(self, character: str) -> tuple[int, bool]:
        """Code virtuel produisant ce caractère sur la disposition active.

        `VkKeyScanW` interroge la disposition réellement installée : sur un
        clavier AZERTY, le « a » se trouve à la position que QWERTY réserve au
        « q », et le « 4 » exige Maj. Convertir avec `ord(...)` supposerait un
        clavier QWERTY et déclencherait une autre touche que celle demandée.
        Cette résolution donne à Windows le même comportement que macOS, où
        AppleScript envoie un caractère et non une position.

        Retourne le code et un indicateur signalant que Maj est nécessaire.
        """
        scan = getattr(self._user32, "VkKeyScanW", None)
        if scan is None:
            # Repli : suppose une disposition QWERTY. Vaut mieux qu'un échec.
            return ord(character.upper()), False

        result = scan(ctypes.c_wchar(character))
        if result == -1:
            raise ActionFailed(f"touche absente du clavier: {character}")

        code = result & 0xFF
        needs_shift = bool(result >> 8 & 0x01)
        return code, needs_shift

    def send_hotkey(self, combination: str) -> None:
        """Envoie une combinaison décrite sous la forme `cmd+shift+n`.

        L'analyse est déléguée au catalogue partagé, afin que l'éditeur de
        configuration applique exactement la même règle que l'exécution.
        """
        # La configuration d'exemple reste commune aux deux OS : le raccourci
        # de capture macOS devient son équivalent natif Outil Capture Windows.
        if [part.strip().lower() for part in combination.split("+")] == [
            "cmd",
            "shift",
            "4",
        ]:
            combination = "win+shift+s"

        try:
            hotkey = parse_hotkey(combination)
        except InvalidHotkey as error:
            raise ActionFailed(str(error)) from error

        modifiers = [modifier.win for modifier in hotkey.modifiers]

        if hotkey.key is not None:
            code = hotkey.key.win
        else:
            code, needs_shift = self._character_code(hotkey.character)
            # Maj imposée par la disposition, sans que l'utilisateur l'ait
            # demandée : sur AZERTY, « 4 » ne s'obtient pas autrement.
            shift = MODIFIER_BY_NAME["shift"].win
            if needs_shift and shift not in modifiers:
                modifiers.append(shift)

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
        try:
            snapshot.audio_outputs = self.list_audio_outputs()
            snapshot.audio_output = self.get_audio_output()
        except Exception:
            snapshot.audio_outputs = []
            snapshot.audio_output = ""
        return snapshot

    def close(self) -> None:
        self._shell.close()
