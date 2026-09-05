#define UNICODE
#define _UNICODE

#include <windows.h>
#include <wchar.h>

static int fail(const wchar_t *message) {
    MessageBoxW(NULL, message, L"3Decks", MB_OK | MB_ICONERROR);
    return 1;
}

int WINAPI wWinMain(
    HINSTANCE instance,
    HINSTANCE previous,
    PWSTR arguments,
    int show
) {
    (void)instance;
    (void)previous;
    (void)show;

    wchar_t package_dir[32768];
    DWORD length = GetModuleFileNameW(NULL, package_dir, 32768);
    if (length == 0 || length >= 32768) {
        return fail(L"Le dossier d'installation de 3Decks est introuvable.");
    }
    wchar_t launcher_path[32768];
    if (wcscpy_s(launcher_path, 32768, package_dir) != 0) {
        return fail(L"Le chemin de lancement de 3Decks est trop long.");
    }
    wchar_t *separator = wcsrchr(package_dir, L'\\');
    if (separator == NULL) {
        return fail(L"Le chemin d'installation de 3Decks est invalide.");
    }
    *separator = L'\0';

    wchar_t python[32768];
    if (swprintf_s(python, 32768, L"%ls\\runtime\\pythonw.exe", package_dir) < 0) {
        return fail(L"Le chemin du moteur Python est trop long.");
    }
    wchar_t command[32768];
    const wchar_t *background =
        arguments != NULL && wcscmp(arguments, L"--background") == 0
            ? L" --background"
            : L"";
    if (swprintf_s(
            command,
            32768,
            L"\"%ls\" -B -m deck3ds --init-if-missing --ui --desktop%ls",
            python,
            background
        ) < 0) {
        return fail(L"La commande de lancement est trop longue.");
    }

    SetEnvironmentVariableW(L"PYTHONDONTWRITEBYTECODE", L"1");
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"DECK3DS_DESKTOP_LAUNCHER", launcher_path);

    STARTUPINFOW startup;
    PROCESS_INFORMATION process;
    ZeroMemory(&startup, sizeof(startup));
    ZeroMemory(&process, sizeof(process));
    startup.cb = sizeof(startup);

    if (!CreateProcessW(
            python,
            command,
            NULL,
            NULL,
            FALSE,
            CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
            NULL,
            package_dir,
            &startup,
            &process
        )) {
        return fail(
            L"3Decks n'a pas pu demarrer. Reinstallez l'application depuis "
            L"le Microsoft Store."
        );
    }

    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exit_code = 1;
    GetExitCodeProcess(process.hProcess, &exit_code);
    CloseHandle(process.hProcess);
    return (int)exit_code;
}
