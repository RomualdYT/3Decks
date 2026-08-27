"""Notifications Windows via l'API officielle UserNotificationListener.

Le fournisseur ne lit jamais ``wpndatabase.db``. Il exige l'identité de paquet,
la capacité ``userNotificationListener`` et l'autorisation explicite de la
personne. Sans ces prérequis, la capacité reste indisponible au lieu de revenir
silencieusement à une base système privée.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import json
import time
from collections.abc import Callable

from .notifications import (
    MAX_AGE_SECONDS,
    MAX_NOTIFICATIONS,
    Notification,
    _icon_for,
)

_CLOCK_TOLERANCE = 60.0
_RETRY_SECONDS = 60.0

_WINDOWS_APP_NAMES = {
    "microsoft.windowscommunicationsapps": "Courrier",
    "microsoft.windowsstore": "Store",
    "microsoft.skypeapp": "Skype",
    "microsoft.outlook": "Outlook",
    "microsoft.teams": "Teams",
    "microsoft.office.outlook": "Outlook",
    "microsoft.windows.explorer": "Explorateur",
    "microsoft.windowsterminal": "Terminal",
    "windows.systemtoast.securityandmaintenance": "Sécurité",
    "windows.systemtoast.windowsupdate": "Mise à jour",
    "windows.systemtoast.bthquickpair": "Bluetooth",
    "chrome": "Chrome",
    "firefox": "Firefox",
    "msedge": "Edge",
    "discord": "Discord",
    "slack": "Slack",
    "spotify": "Spotify",
    "code": "VS Code",
    "steam": "Steam",
    "thunderbird": "Thunderbird",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
}


def readable_windows_name(aumid: str) -> str:
    """Produit un nom court quand WinRT ne fournit pas de nom d'affichage."""
    cleaned = aumid.strip()
    if not cleaned:
        return ""

    package = cleaned.split("!")[0].split("_")[0]
    if "\\" in package or "/" in package:
        package = package.replace("\\", "/").rsplit("/", 1)[-1]
    for suffix in (".lnk", ".exe"):
        if package.lower().endswith(suffix):
            package = package[: -len(suffix)]

    known = _WINDOWS_APP_NAMES.get(package.lower())
    if known:
        return known

    tail = package.rsplit(".", 1)[-1] if "." in package else package
    return tail[:1].upper() + tail[1:] if tail else package


_POWERSHELL = r'''
try {
  $ErrorActionPreference = 'Stop'
  Add-Type -AssemblyName System.Runtime.WindowsRuntime -ErrorAction Stop

  function Wait-Deck3DSAsync($operation, $resultType) {
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() |
      Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } |
      Select-Object -First 1
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
  }

  $listenerType = [Windows.UI.Notifications.Management.UserNotificationListener,Windows.UI.Notifications.Management,ContentType=WindowsRuntime]
  $accessType = [Windows.UI.Notifications.Management.UserNotificationListenerAccessStatus,Windows.UI.Notifications.Management,ContentType=WindowsRuntime]
  $listener = $listenerType::Current
  $status = $listener.GetAccessStatus()

  if ($status -eq $accessType::Unspecified -and __REQUEST_ACCESS__) {
    $status = Wait-Deck3DSAsync ($listener.RequestAccessAsync()) $accessType
  }

  $items = New-Object System.Collections.Generic.List[object]
  if ($status -eq $accessType::Allowed) {
    $notificationType = [Windows.UI.Notifications.UserNotification,Windows.UI.Notifications,ContentType=WindowsRuntime]
    $listType = [System.Collections.Generic.IReadOnlyList`1].MakeGenericType($notificationType)
    $kindsType = [Windows.UI.Notifications.NotificationKinds,Windows.UI.Notifications,ContentType=WindowsRuntime]
    $bindingType = [Windows.UI.Notifications.KnownNotificationBindings,Windows.UI.Notifications,ContentType=WindowsRuntime]
    $notifications = Wait-Deck3DSAsync ($listener.GetNotificationsAsync($kindsType::Toast)) $listType

    foreach ($entry in $notifications) {
      try {
        $binding = $entry.Notification.Visual.GetBinding($bindingType::ToastGeneric)
        if ($null -eq $binding) { continue }
        $texts = @($binding.GetTextElements() | ForEach-Object { ([string]$_.Text).Trim() } | Where-Object { $_ })
        if ($texts.Count -eq 0) { continue }
        $body = if ($texts.Count -gt 1) { [string]::Join(' ', $texts[1..($texts.Count - 1)]) } else { '' }
        $items.Add([PSCustomObject]@{
          id = [string]$entry.Id
          created = [long]$entry.CreationTime.ToUnixTimeSeconds()
          identifier = [string]$entry.AppInfo.AppUserModelId
          app = [string]$entry.AppInfo.DisplayInfo.DisplayName
          title = [string]$texts[0]
          body = $body
        })
      } catch {
        # Une notification mal formée ne doit pas masquer les autres.
      }
    }
  }

  [PSCustomObject]@{
    status = [string]$status
    notifications = [object[]]$items.ToArray()
  } | ConvertTo-Json -Depth 5 -Compress
} catch {
  [PSCustomObject]@{
    status = 'Error'
    error = $_.Exception.Message
    notifications = [object[]]@()
  } | ConvertTo-Json -Depth 5 -Compress
}
'''


def _script(request_access: bool) -> str:
    return _POWERSHELL.replace(
        "__REQUEST_ACCESS__", "$true" if request_access else "$false"
    )


def _json_payload(raw: str) -> dict[str, object]:
    """Retient le dernier objet JSON, malgré les avertissements PowerShell."""
    for line in reversed(raw.splitlines()):
        try:
            candidate = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(candidate, dict):
            return candidate
    raise ValueError("réponse WinRT invalide")


class WindowsNotificationReader:
    """Lecteur WinRT avec cache, permission et détection des nouveautés."""

    def __init__(self, run: Callable[..., str], request_access: bool = True) -> None:
        self._run = run
        self.available = False
        self.access_status = "Unknown"
        self.last_error = ""
        self._last_key = ""
        self._cache: list[Notification] = []
        self._next_retry = 0.0
        self._refresh(request_access=request_access)

    def _refresh(self, request_access: bool = False) -> list[Notification]:
        try:
            raw = self._run(_script(request_access), timeout=60.0)
            payload = _json_payload(raw)
        except Exception as error:
            self.available = False
            self.access_status = "Error"
            self.last_error = str(error)
            self._next_retry = time.monotonic() + _RETRY_SECONDS
            return self._cache

        if not isinstance(payload, dict):
            self.available = False
            self.access_status = "Error"
            self.last_error = "réponse WinRT invalide"
            self._next_retry = time.monotonic() + _RETRY_SECONDS
            return self._cache

        self.access_status = str(payload.get("status") or "Unknown")
        self.available = self.access_status == "Allowed"
        self.last_error = str(payload.get("error") or "")
        if not self.available:
            self._cache = []
            self._next_retry = time.monotonic() + _RETRY_SECONDS
            return []

        rows = payload.get("notifications")
        if not isinstance(rows, list):
            rows = []
        self._cache = self._decode(rows)
        self._next_retry = 0.0
        return self._cache

    def _decode(self, rows: list[object]) -> list[Notification]:
        now = time.time()
        decoded: list[tuple[int, Notification]] = []
        seen: set[str] = set()

        for raw in rows:
            if not isinstance(raw, dict):
                continue
            try:
                created = int(raw.get("created") or 0)
            except (TypeError, ValueError):
                continue
            age = now - created
            if age < -_CLOCK_TOLERANCE or age > MAX_AGE_SECONDS:
                continue
            age = max(0.0, age)

            identifier = str(raw.get("identifier") or "").strip()
            app = str(raw.get("app") or "").strip()
            app = app or readable_windows_name(identifier)
            title = str(raw.get("title") or "").strip()
            body = str(raw.get("body") or "").strip()
            if not title and not body:
                continue

            key = "|".join(
                (identifier, str(raw.get("id") or ""), title, body)
            )
            if key in seen:
                continue
            seen.add(key)
            decoded.append(
                (
                    created,
                    Notification(
                        app=app,
                        title=title or app,
                        body=body,
                        icon=_icon_for(app),
                        age=int(age),
                        bundle=identifier,
                        key=key,
                    ),
                )
            )

        decoded.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in decoded[:MAX_NOTIFICATIONS]]

    def read(self) -> list[Notification]:
        if not self.available and time.monotonic() < self._next_retry:
            return []
        return self._refresh(request_access=self.access_status == "Unspecified")

    def take_new(self, notifications: list[Notification]) -> Notification | None:
        if not notifications:
            return None

        newest = notifications[0]
        if not self._last_key:
            self._last_key = newest.key
            return None
        if newest.key == self._last_key:
            return None

        self._last_key = newest.key
        return newest
