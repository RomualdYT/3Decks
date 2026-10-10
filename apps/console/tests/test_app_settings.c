#undef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <3ds.h>

struct in_addr __3dslink_host;
static int sync_error;
static int rename_error;

#ifdef SETTINGS_TEST_NATIVE
/* Use the production 3DS replacement path, with host files at the SDK boundary. */
#define __3DS__
typedef int FS_Archive;
typedef struct { const char *data; } FS_Path;
#define ARCHIVE_SDMC 9
#define PATH_EMPTY 1
#define PATH_ASCII 3
static bool fail_replace;
static FS_Path fsMakePath(int type, const char *path)
{
	(void)type;
	return (FS_Path){path};
}
static Result FSUSER_OpenArchive(FS_Archive *archive, int type, FS_Path path)
{
	(void)type; (void)path;
	*archive = 1;
	return 0;
}
static Result FSUSER_CloseArchive(FS_Archive archive)
{
	(void)archive;
	return 0;
}
static Result FSUSER_RenameFile(FS_Archive from, FS_Path old_path,
                               FS_Archive to, FS_Path new_path)
{
	(void)from; (void)to;
	if (rename_error || (fail_replace && strstr(old_path.data, "settings.tmp"))) {
		fail_replace = false;
		return (Result)0xC82044BE;
	}
	char old_name[128], new_name[128];
	snprintf(old_name, sizeof(old_name), "sdmc:%s", old_path.data);
	snprintf(new_name, sizeof(new_name), "sdmc:%s", new_path.data);
	return rename(old_name, new_name) == 0 ? 0 : (Result)0xC82044BE;
}
#endif

static int settings_test_fsync(int fd)
{
	if (sync_error) { errno = sync_error; return -1; }
	return fsync(fd);
}

#ifndef SETTINGS_TEST_NATIVE
static int settings_test_rename(const char *old_path, const char *new_path)
{
	if (rename_error) { errno = rename_error; return -1; }
	return rename(old_path, new_path);
}
#endif

/* Exercise production persistence with failures at the filesystem boundary. */
#define fsync settings_test_fsync
#ifndef SETTINGS_TEST_NATIVE
#define rename settings_test_rename
#endif
#include "../source/platform/app_settings.c"
#undef fsync
#undef rename

int main(void)
{
	char directory[] = "/tmp/3decks-settings-XXXXXX";
	assert(mkdtemp(directory));
	assert(chdir(directory) == 0);
	Settings settings, loaded;
	app_settings_load(&settings);
	assert(!settings.configured);
	assert(!app_settings_save(&settings));
	assert(strstr(app_settings_save_error(), "mkdir 3ds:"));
	assert(mkdir("sdmc:", 0777) == 0);
	assert(app_settings_save(&settings));
	assert(app_settings_save_error()[0] == '\0');
	strcpy(settings.host, "192.168.1.42");
	memset(settings.token, 'a', 64);
	settings.token[64] = '\0';
	assert(app_settings_save(&settings));
	app_settings_load(&loaded);
	assert(loaded.configured && strcmp(loaded.host, settings.host) == 0);
	assert(strcmp(loaded.token, settings.token) == 0);
	strcpy(settings.host, "192.168.1.99");
	sync_error = EIO;
	assert(!app_settings_save(&settings));
	assert(strstr(app_settings_save_error(), "fsync:"));
	assert(access(SETTINGS_TMP_PATH, F_OK) != 0);
	app_settings_load(&loaded);
	assert(strcmp(loaded.host, "192.168.1.42") == 0);
	sync_error = 0;
	rename_error = EACCES;
	assert(!app_settings_save(&settings));
	assert(strstr(app_settings_save_error(), "rename"));
	assert(access(SETTINGS_TMP_PATH, F_OK) != 0);
	app_settings_load(&loaded);
	assert(strcmp(loaded.host, "192.168.1.42") == 0);
	rename_error = 0;
#ifdef SETTINGS_TEST_NATIVE
	fail_replace = true;
	assert(!app_settings_save(&settings));
	app_settings_load(&loaded);
	assert(strcmp(loaded.host, "192.168.1.42") == 0);
	assert(access(SETTINGS_BACKUP_PATH, F_OK) != 0);
#endif
	assert(app_settings_save(&settings));
	assert(app_settings_save_error()[0] == '\0');
	assert(rename(SETTINGS_PATH, SETTINGS_BACKUP_PATH) == 0);
	app_settings_load(&loaded);
	assert(loaded.configured && strcmp(loaded.host, settings.host) == 0);
	assert(strcmp(loaded.token, settings.token) == 0);
	assert(rename(SETTINGS_BACKUP_PATH, SETTINGS_PATH) == 0);
	assert(remove(SETTINGS_PATH) == 0);
	assert(rmdir("sdmc:/3ds/deck3ds") == 0);
	FILE *conflict = fopen("sdmc:/3ds/deck3ds", "w");
	assert(conflict && fclose(conflict) == 0);
	assert(!app_settings_save(&settings));
	assert(strstr(app_settings_save_error(), "mkdir deck3ds:"));
	assert(remove("sdmc:/3ds/deck3ds") == 0);
	assert(rmdir("sdmc:/3ds") == 0);
	assert(rmdir("sdmc:") == 0);
	assert(chdir("/tmp") == 0);
	assert(rmdir(directory) == 0);
	puts("settings persistence and failure diagnostics: OK");
	return 0;
}
