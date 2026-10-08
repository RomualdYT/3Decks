//! Native extension API 1. Packages are inert until the user approves their
//! fingerprint; target-specific executables speak bounded JSON-lines stdio.
mod runtime;
use runtime::Runtime;
pub use runtime::ActionRequest;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::{HashMap, HashSet},
    fs,
    io::{Read, Write},
    path::{Component, Path, PathBuf},
    process::Stdio,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt, BufReader},
    process::{Child, ChildStdin, ChildStdout, Command},
};

const MAX_MESSAGE: usize = 64 * 1024;
const MAX_ARCHIVE: u64 = 4 * 1024 * 1024;
const MAX_PACKAGE: u64 = 16 * 1024 * 1024;
const MAX_FILES: usize = 256;
const MAX_PACKAGES: usize = 64;

struct Worker {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    sequence: u64,
}

impl Worker {
    async fn call(&mut self, method: &str, params: Value) -> Result<Value, String> {
        self.sequence += 1;
        let request = json!({"id":self.sequence,"method":method,"params":params});
        let mut data = serde_json::to_vec(&request).map_err(|e| e.to_string())?;
        if data.len() > MAX_MESSAGE {
            return Err("Extension request exceeds 64 KiB".into());
        }
        data.push(b'\n');
        let io = async {
            self.stdin
                .write_all(&data)
                .await
                .map_err(|e| e.to_string())?;
            self.stdin.flush().await.map_err(|e| e.to_string())?;
            let mut response = Vec::new();
            loop {
                let byte = self.stdout.read_u8().await.map_err(|e| e.to_string())?;
                if byte == b'\n' {
                    break;
                }
                response.push(byte);
                if response.len() > MAX_MESSAGE {
                    return Err("Extension response exceeds 64 KiB".into());
                }
            }
            let result: Value =
                serde_json::from_slice(&response).map_err(|_| "Invalid extension JSON response")?;
            if result["id"].as_u64() != Some(self.sequence) {
                return Err("Extension response ID mismatch".into());
            }
            if result.get("error").is_some_and(|error| !error.is_null()) {
                return Err("Extension handler failed; contact its author".into());
            }
            Ok(result["result"].clone())
        };
        tokio::time::timeout(Duration::from_secs(5), io)
            .await
            .map_err(|_| "Extension timed out (5 s limit)".to_owned())?
    }
}

impl Drop for Worker {
    fn drop(&mut self) {
        let _ = self.child.start_kill();
    }
}

struct Package {
    manifest: Value,
    path: PathBuf,
    digest: String,
    enabled: bool,
    approved: String,
    status: String,
    error: String,
    settings: Value,
    worker: Option<Runtime>,
    snapshot: Value,
    updated_at: f64,
}

impl Package {
    fn status(&self) -> String {
        self.worker.as_ref().map(Runtime::status).unwrap_or_else(|| self.status.clone())
    }
    fn view(&self) -> runtime::View {
        self.worker.as_ref().map(Runtime::view).unwrap_or_else(|| runtime::View {
            status: self.status.clone(), error: self.error.clone(),
            snapshot: self.snapshot.clone(), updated_at: self.updated_at,
        })
    }
}

pub struct ExtensionHost {
    root: PathBuf,
    packages: HashMap<String, Package>,
    errors: Vec<String>,
    registry: Value,
    registry_error: Option<String>,
}

impl ExtensionHost {
    pub fn new(root: PathBuf) -> Result<Self, String> {
        fs::create_dir_all(root.join("packages")).map_err(|e| e.to_string())?;
        let mut host = Self {
            root,
            packages: HashMap::new(),
            errors: Vec::new(),
            registry: json!({}),
            registry_error: None,
        };
        host.rescan()?;
        Ok(host)
    }

    pub fn describe(&self) -> Value {
        let mut packages: Vec<_> = self.packages.values().collect();
        packages.sort_by_key(|package| package.manifest["id"].as_str().unwrap_or("").to_owned());
        let extensions: Vec<Value> = packages.into_iter().map(|package| {
            let view = package.view();
            let secret_names: HashSet<_> = package.manifest["settings"].as_array().into_iter().flatten()
                .filter(|field| field["type"] == "password").filter_map(|field| field["name"].as_str()).collect();
            let public_settings: serde_json::Map<String, Value> = package.settings.as_object().into_iter().flat_map(|settings| settings.iter())
                .filter(|(name, _)| !secret_names.contains(name.as_str())).map(|(name, value)| (name.clone(), value.clone())).collect();
            let secret_fields_set: Vec<&str> = secret_names.into_iter().filter(|name| package.settings[*name].as_str().is_some_and(|value| !value.is_empty())).collect();
            json!({"manifest":package.manifest,"digest":package.digest,"enabled":package.enabled,"status":view.status,
                "error":view.error,"updated_at":view.updated_at,"settings":public_settings,"secret_fields_set":secret_fields_set})
        }).collect();
        json!({"api_version":1,"directory":self.root,"extensions":extensions,"errors":self.errors})
    }

    pub fn catalog(&self) -> Value {
        let mut actions = Vec::new();
        let mut sources = Vec::new();
        let mut dashboards = Vec::new();
        for package in self.packages.values() {
            let manifest = &package.manifest;
            let id = manifest["id"].as_str().unwrap_or("");
            let supported = package.status() == "ready";
            for (group, output) in [
                ("actions", &mut actions),
                ("sources", &mut sources),
                ("dashboards", &mut dashboards),
            ] {
                if let Some(specs) = manifest[group].as_array() {
                    for spec in specs {
                        let Some(name) = spec["id"].as_str() else {
                            continue;
                        };
                        let mut entry = spec.clone();
                        let key = format!("ext:{id}/{name}");
                        entry["extension"] = json!(id);
                        entry["extension_name"] = manifest["name"].clone();
                        entry["supported"] = json!(supported);
                        entry["capability"] = Value::Null;
                        if group == "actions" {
                            entry["kind"] = json!(key);
                            entry["category"] = json!("extensions");
                        } else {
                            entry["name"] = json!(key);
                        }
                        output.push(entry);
                    }
                }
            }
        }
        json!({"actions":actions,"sources":sources,"dashboards":dashboards})
    }

    pub fn snapshots(&self) -> Value {
        let mut out = serde_json::Map::new();
        for (id, package) in &self.packages {
            let view = package.view();
            if view.status == "ready" {
                out.insert(id.clone(), view.snapshot);
            }
        }
        Value::Object(out)
    }

    pub fn rescan(&mut self) -> Result<(), String> {
        self.registry_error = None;
        self.registry = match read_object(&self.root.join("registry.json")) {
            Ok(value) => value,
            Err(error) => {
                self.registry_error = Some(error);
                json!({})
            }
        };
        self.errors = self.registry_error.clone().into_iter().collect();
        let mut paths: Vec<_> = fs::read_dir(self.root.join("packages"))
            .map_err(|e| e.to_string())?
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .filter(|path| path.is_dir() && !path.is_symlink())
            .collect();
        paths.sort();
        if paths.len() > MAX_PACKAGES {
            self.errors
                .push("Maximum 64 installed extensions; extra packages ignored".into());
        }
        let mut found = HashMap::new();
        for path in paths.into_iter().take(MAX_PACKAGES) {
            let name = path
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or("")
                .to_owned();
            let loaded = (|| -> Result<Package, String> {
                let manifest = load_manifest(&path)?;
                if manifest["id"] != name {
                    return Err("Package directory name does not match manifest ID".into());
                }
                let digest = fingerprint(&path)?;
                let saved = &self.registry[&name];
                let approved = saved["approved"].as_str().unwrap_or("").to_owned();
                let enabled = saved["enabled"].as_bool() == Some(true);
                let settings =
                    read_object(&self.root.join("data").join(&name).join("settings.json"))?;
                let status = if !manifest["binaries"][target_key()].is_string() {
                    "unsupported"
                } else if self.registry_error.is_some() || (enabled && approved != digest) {
                    "untrusted"
                } else if enabled {
                    "starting"
                } else {
                    "disabled"
                };
                Ok(Package {
                    manifest,
                    path: path.clone(),
                    digest,
                    enabled,
                    approved,
                    status: status.into(),
                    error: String::new(),
                    settings,
                    worker: None,
                    snapshot: json!({}),
                    updated_at: 0.0,
                })
            })();
            match loaded {
                Ok(package) => {
                    found.insert(name, package);
                }
                Err(error) => self.errors.push(format!("{name}: {error}")),
            }
        }
        self.packages = found;
        Ok(())
    }

    pub async fn manage(&mut self, request: Value) -> Result<Value, String> {
        let operation = request["operation"]
            .as_str()
            .ok_or("Extension operation missing")?;
        let id = request["id"].as_str().unwrap_or("");
        match operation {
            "rescan" => self.rescan()?,
            "install" => {
                let path = request["path"].as_str().ok_or("Archive path missing")?;
                install_archive(Path::new(path), &self.root)?;
                self.rescan()?;
            }
            "enable" => {
                if self.registry_error.is_some() {
                    return Err("Repair registry.json before approving extensions".into());
                }
                let package = self.packages.get_mut(id).ok_or("Extension not installed")?;
                if request["trust"] != true
                    || request["digest"].as_str() != Some(package.digest.as_str())
                    || fingerprint(&package.path)? != package.digest
                {
                    return Err("Approve the current package fingerprint first".into());
                }
                if !package.manifest["binaries"][target_key()].is_string() {
                    return Err(
                        "No native binary for this operating system and architecture".into(),
                    );
                }
                package.enabled = true;
                package.approved = package.digest.clone();
                package.status = "starting".into();
                package.error.clear();
                self.save_registry(id)?;
                self.start(id)?;
            }
            "disable" | "restart" => {
                let package = self.packages.get_mut(id).ok_or("Extension not installed")?;
                if operation == "restart"
                    && (!package.enabled || package.approved != package.digest)
                {
                    return Err("Approve and enable the extension first".into());
                }
                if let Some(runtime) = package.worker.take() {
                    runtime.stop().await;
                }
                package.snapshot = json!({});
                package.updated_at = 0.0;
                package.status = if operation == "restart" {
                    "starting"
                } else {
                    "disabled"
                }
                .into();
                if operation == "disable" {
                    package.enabled = false;
                    self.save_registry(id)?;
                } else {
                    self.start(id)?;
                }
            }
            "configure" => {
                let package = self.packages.get_mut(id).ok_or("Extension not installed")?;
                let values = request["settings"]
                    .as_object()
                    .ok_or("Settings must be an object")?;
                let mut merged = package.settings.as_object().cloned().unwrap_or_default();
                for (name, value) in values {
                    if !(package.manifest["settings"]
                        .as_array()
                        .is_some_and(|fields| fields.iter().any(|field| field["name"] == *name)))
                    {
                        return Err(format!("Unknown setting: {name}"));
                    }
                    if value != "" {
                        merged.insert(name.clone(), value.clone());
                    }
                }
                let merged = Value::Object(merged);
                validate_values(&package.manifest["settings"], &merged)?;
                let path = self.root.join("data").join(id).join("settings.json");
                write_private_json(&path, &merged)?;
                package.settings = merged;
                if let Some(runtime) = package.worker.take() {
                    runtime.stop().await;
                }
                package.snapshot = json!({});
                if package.enabled {
                    package.status = "starting".into();
                    self.start(id)?;
                }
            }
            "remove" => {
                if request["confirm"] != true {
                    return Err("Confirm removal first".into());
                }
                let mut package = self.packages.remove(id).ok_or("Extension not installed")?;
                if let Some(runtime) = package.worker.take() {
                    runtime.stop().await;
                }
                fs::create_dir_all(self.root.join("trash")).map_err(|e| e.to_string())?;
                let target =
                    self.root
                        .join("trash")
                        .join(format!("{}-{}", id, rand::random::<u64>()));
                fs::rename(&package.path, target).map_err(|e| e.to_string())?;
                if let Some(registry) = self.registry.as_object_mut() {
                    registry.remove(id);
                }
                write_private_json(&self.root.join("registry.json"), &self.registry)?;
            }
            _ => return Err("Unknown extension operation".into()),
        }
        Ok(json!({"ok":true}))
    }

    fn save_registry(&mut self, id: &str) -> Result<(), String> {
        let package = self.packages.get(id).ok_or("Extension not installed")?;
        self.registry[id] = json!({"enabled":package.enabled,"approved":package.approved});
        write_private_json(&self.root.join("registry.json"), &self.registry)
    }

    fn start(&mut self, id: &str) -> Result<(), String> {
        let package = self.packages.get_mut(id).ok_or("Extension not installed")?;
        if package.worker.is_some() {
            return Ok(());
        }
        if !package.enabled || package.approved != fingerprint(&package.path)? {
            package.status = "untrusted".into();
            return Err("Package changed; approve it again".into());
        }
        let executable = package.manifest["binaries"][target_key()]
            .as_str()
            .ok_or("No native binary for this target")?;
        let program = package.path.join(portable_path(executable)?);
        if !program.is_file() {
            return Err("Native extension binary missing".into());
        }
        let mut command = Command::new(program);
        #[cfg(target_os = "windows")]
        command.creation_flags(windows::Win32::System::Threading::CREATE_NO_WINDOW.0);
        command
            .current_dir(&package.path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .kill_on_drop(true);
        let mut child = command
            .spawn()
            .map_err(|e| format!("Extension runtime could not start: {e}"))?;
        let stdin = child.stdin.take().ok_or("Extension stdin unavailable")?;
        let stdout = child.stdout.take().ok_or("Extension stdout unavailable")?;
        let worker = Worker {
            child,
            stdin,
            stdout: BufReader::new(stdout),
            sequence: 0,
        };
        let data_dir = self.root.join("data").join(id).join("storage");
        fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;
        let settings = validate_values(&package.manifest["settings"], &package.settings)?;
        package.worker = Some(Runtime::spawn(worker, package.manifest.clone(), json!({"api_version":1,"extension_id":id,"settings":settings,"data_dir":data_dir,"platform":platform()})));
        Ok(())
    }

    /// Start due runtimes without waiting for any extension process.
    pub fn refresh(&mut self) {
        let ids: Vec<_> = self.packages.iter()
            .filter(|(_, package)| package.enabled && package.worker.is_none() && package.status == "starting")
            .map(|(id, _)| id.clone()).collect();
        for id in ids {
            if let Err(error) = self.start(&id) {
                if let Some(package) = self.packages.get_mut(&id) {
                    package.status = "error".into();
                    package.error = error;
                }
            }
        }
    }

    pub fn prepare_action(&self, reference: &str, arguments: &Value) -> Result<ActionRequest, String> {
        let (id, action) = parse_reference(reference).ok_or("Invalid extension action reference")?;
        let item = self.packages.get(id).ok_or("Extension missing")?;
        if !item.enabled || !matches!(item.status().as_str(), "starting" | "ready") {
            return Err("Extension unavailable; check Extensions".into());
        }
        let spec = item.manifest["actions"].as_array()
            .and_then(|actions| actions.iter().find(|entry| entry["id"] == action))
            .ok_or("Extension action not declared")?;
        let checked = validate_values(&spec["arguments"], arguments)?;
        Ok(item.worker.as_ref().ok_or("Extension worker unavailable")?
            .action(json!({"action":action,"arguments":checked})))
    }

    #[cfg(test)]
    pub async fn poll_all(&mut self) {
        self.refresh();
        for package in self.packages.values() {
            if let Some(runtime) = &package.worker { let _ = runtime.poll().await; }
        }
    }

    #[cfg(test)]
    pub async fn execute(&self, reference: &str, arguments: &Value) -> Result<String, String> {
        self.prepare_action(reference, arguments)?.run().await
    }

}

fn platform() -> &'static str {
    if cfg!(target_os = "macos") {
        "darwin"
    } else if cfg!(target_os = "windows") {
        "win32"
    } else {
        "linux"
    }
}
fn target_key() -> &'static str {
    match (platform(), std::env::consts::ARCH) {
        ("darwin", "aarch64") => "darwin-aarch64",
        ("darwin", "x86_64") => "darwin-x86_64",
        ("win32", "aarch64") => "win32-aarch64",
        ("win32", "x86_64") => "win32-x86_64",
        ("linux", "aarch64") => "linux-aarch64",
        ("linux", "x86_64") => "linux-x86_64",
        _ => "unsupported",
    }
}
fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}
fn parse_reference(value: &str) -> Option<(&str, &str)> {
    let rest = value.strip_prefix("ext:")?;
    let (id, name) = rest.split_once('/')?;
    if valid_id(id) && valid_key(name) {
        Some((id, name))
    } else {
        None
    }
}
fn valid_id(value: &str) -> bool {
    (3..=48).contains(&value.len())
        && value.starts_with(|c: char| c.is_ascii_lowercase())
        && value
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'.' || b == b'-')
}
fn valid_key(value: &str) -> bool {
    (1..=32).contains(&value.len())
        && value.starts_with(|c: char| c.is_ascii_lowercase())
        && value
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-')
}
fn read_object(path: &Path) -> Result<Value, String> {
    if !path.exists() {
        return Ok(json!({}));
    }
    let data = fs::read(path).map_err(|e| e.to_string())?;
    let value: Value = serde_json::from_slice(&data).map_err(|e| e.to_string())?;
    if !value.is_object() {
        return Err(format!("{} must be an object", path.display()));
    }
    Ok(value)
}
fn write_private_json(path: &Path, value: &Value) -> Result<(), String> {
    fs::create_dir_all(path.parent().ok_or("Invalid path")?).map_err(|e| e.to_string())?;
    let temporary = path.with_extension(format!("{}.tmp", rand::random::<u64>()));
    let mut options = fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(&temporary).map_err(|e| e.to_string())?;
    file.write_all(&serde_json::to_vec_pretty(value).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    file.sync_all().map_err(|e| e.to_string())?;
    fs::rename(&temporary, path).map_err(|e| e.to_string())
}

fn portable_path(name: &str) -> Result<PathBuf, String> {
    if name.is_empty()
        || name.contains('\\')
        || name.contains(':')
        || name.chars().any(|c| c.is_control())
    {
        return Err("Unsafe package path".into());
    }
    let path = Path::new(name);
    if path
        .components()
        .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err("Unsafe package path".into());
    }
    for part in path.components() {
        let text = part.as_os_str().to_string_lossy();
        let stem = text.split('.').next().unwrap_or("").to_ascii_uppercase();
        if text.ends_with(['.', ' '])
            || [
                "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7",
                "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8",
                "LPT9",
            ]
            .contains(&stem.as_str())
        {
            return Err("Non-portable package path".into());
        }
    }
    Ok(path.to_path_buf())
}

fn fingerprint(root: &Path) -> Result<String, String> {
    let mut paths = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    let mut size = 0u64;
    while let Some(dir) = stack.pop() {
        for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
            let path = entry.map_err(|e| e.to_string())?.path();
            if path.is_symlink() {
                return Err("Package symlink forbidden".into());
            }
            if path.is_dir() {
                stack.push(path);
            } else if path.is_file() {
                size += path.metadata().map_err(|e| e.to_string())?.len();
                paths.push(path);
                if paths.len() > MAX_FILES || size > MAX_PACKAGE {
                    return Err("Package exceeds limits".into());
                }
            }
        }
    }
    paths.sort();
    let mut hash = Sha256::new();
    for path in paths {
        let name = path
            .strip_prefix(root)
            .map_err(|e| e.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        portable_path(&name)?;
        let bytes = fs::read(&path).map_err(|e| e.to_string())?;
        hash.update((name.len() as u32).to_be_bytes());
        hash.update(name.as_bytes());
        hash.update((bytes.len() as u64).to_be_bytes());
        hash.update(bytes);
    }
    Ok(hex::encode(hash.finalize()))
}

fn load_manifest(root: &Path) -> Result<Value, String> {
    let path = root.join("extension.json");
    if path.metadata().map_err(|e| e.to_string())?.len() > MAX_MESSAGE as u64 {
        return Err("Manifest exceeds 64 KiB".into());
    }
    let data = fs::read(path).map_err(|e| e.to_string())?;
    let mut value: Value = serde_json::from_slice(&data).map_err(|e| e.to_string())?;
    if value["api_version"] != 1 {
        return Err("Unsupported extension API".into());
    }
    let id = value["id"].as_str().ok_or("Extension ID missing")?;
    if !valid_id(id) {
        return Err("Invalid extension ID".into());
    }
    if !value["version"]
        .as_str()
        .is_some_and(|version| version.len() < 65 && version.split('.').count() >= 3)
    {
        return Err("Invalid extension version".into());
    }
    for field in ["name", "description"] {
        if !value[field].is_string() && !value[field]["en"].is_string() {
            return Err(format!("{field}: English text required"));
        }
    }
    if !value["author"]
        .as_str()
        .is_some_and(|author| !author.is_empty() && author.len() <= 100)
    {
        return Err("Invalid author".into());
    }
    if value["runtime"] != "native" {
        return Err("Only native extension packages are supported".into());
    }
    if value.get("command").is_some() || value.get("entrypoint").is_some() {
        return Err("Native extensions declare binaries, not commands or scripts".into());
    }
    let binaries = value["binaries"]
        .as_object()
        .ok_or("Native binaries missing")?;
    if binaries.is_empty() || binaries.len() > 6 {
        return Err("Expected 1–6 native binaries".into());
    }
    let mut platforms = HashSet::new();
    for (target, binary) in binaries {
        if !matches!(
            target.as_str(),
            "darwin-aarch64"
                | "darwin-x86_64"
                | "win32-aarch64"
                | "win32-x86_64"
                | "linux-aarch64"
                | "linux-x86_64"
        ) {
            return Err("Unsupported native target".into());
        }
        let relative = portable_path(binary.as_str().ok_or("Invalid native binary path")?)?;
        if relative.components().next() != Some(Component::Normal("bin".as_ref()))
            || !root.join(&relative).is_file()
            || root.join(&relative).is_symlink()
        {
            return Err("Native binary must be a package-local file in bin/".into());
        }
        platforms.insert(target.split('-').next().unwrap());
    }
    let mut platforms: Vec<_> = platforms.into_iter().collect();
    platforms.sort_unstable();
    value["platforms"] = json!(platforms);
    if !value["platforms"].as_array().is_some_and(|platforms| {
        !platforms.is_empty()
            && platforms
                .iter()
                .all(|platform| matches!(platform.as_str(), Some("darwin" | "win32" | "linux")))
    }) {
        return Err("Invalid extension platforms".into());
    }
    if !value["permissions"].is_array() {
        value["permissions"] = json!([]);
    }
    if !value["permissions"].as_array().is_some_and(|permissions| {
        permissions.iter().all(|permission| {
            matches!(
                permission.as_str(),
                Some("network" | "filesystem" | "system" | "notifications")
            )
        })
    }) {
        return Err("Invalid extension permission".into());
    }
    if !value["settings"].is_array() {
        value["settings"] = json!([]);
    }
    if value["settings"]
        .as_array()
        .is_some_and(|settings| settings.len() > 16)
    {
        return Err("Too many extension settings".into());
    }
    if let Some(settings) = value["settings"].as_array_mut() {
        let mut names = HashSet::new();
        for field in settings {
            let name = field["name"]
                .as_str()
                .ok_or("Setting name missing")?
                .to_owned();
            if !valid_key(&name) || !names.insert(name.clone()) {
                return Err("Invalid or duplicate setting name".into());
            }
            let kind = field["type"].as_str().unwrap_or("text").to_owned();
            if !matches!(
                kind.as_str(),
                "text" | "password" | "number" | "boolean" | "select"
            ) {
                return Err("Invalid setting type".into());
            }
            if kind == "password" && !field["default"].is_null() {
                return Err("Password defaults are forbidden".into());
            }
            field["type"] = json!(kind);
            if field["label"].is_null() {
                field["label"] = json!(name);
            }
            if field["description"].is_null() {
                field["description"] = json!("");
            }
            if field["required"].is_null() {
                field["required"] = json!(false);
            }
            if kind == "select"
                && !field["choices"]
                    .as_array()
                    .is_some_and(|choices| (1..=32).contains(&choices.len()))
            {
                return Err("Select setting needs 1–32 choices".into());
            }
        }
    }
    let interval = value["poll_interval"].as_f64().unwrap_or(2.0);
    if !(0.5..=60.0).contains(&interval) {
        return Err("Invalid poll interval".into());
    }
    value["poll_interval"] = json!(interval);
    for (group, max) in [("actions", 32), ("sources", 8), ("dashboards", 8)] {
        if !value[group].is_array() {
            value[group] = json!([]);
        }
        let items = value[group].as_array_mut().unwrap();
        if items.len() > max {
            return Err(format!("Too many {group}"));
        }
        let mut seen = HashSet::new();
        for entry in items {
            let name = entry["id"]
                .as_str()
                .ok_or("Contribution ID missing")?
                .to_owned();
            if !valid_key(&name) || !seen.insert(name) {
                return Err(format!("Invalid or duplicate {group} ID"));
            }
            if !entry["title"].is_string() && !entry["title"]["en"].is_string() {
                return Err(format!("{group} title is required"));
            }
            if entry["description"].is_null() {
                entry["description"] = entry["title"].clone();
            }
            if entry["icon"].is_null() {
                entry["icon"] = json!("app");
            }
            if entry["color"].is_null() {
                entry["color"] = json!("#66CB10");
            }
            if !entry["icon"].as_str().is_some_and(|icon| icon.len() <= 16)
                || !entry["color"].as_str().is_some_and(color_ok)
            {
                return Err(format!("Invalid {group} icon or color"));
            }
        }
    }
    if let Some(actions) = value["actions"].as_array_mut() {
        for action in actions {
            if !action["arguments"].is_array() {
                action["arguments"] = json!([]);
            }
        }
    }
    Ok(value)
}

fn validate_values(specs: &Value, values: &Value) -> Result<Value, String> {
    let supplied = values.as_object().ok_or("Parameters must be an object")?;
    let fields = specs.as_array().ok_or("Invalid field declarations")?;
    if fields.len() > 16 {
        return Err("Too many fields".into());
    }
    let mut output = serde_json::Map::new();
    for key in supplied.keys() {
        if !fields.iter().any(|field| field["name"] == *key) {
            return Err(format!("Unknown field: {key}"));
        }
    }
    for field in fields {
        let name = field["name"].as_str().ok_or("Field name missing")?;
        if !valid_key(name) {
            return Err("Invalid field name".into());
        }
        let value = supplied.get(name).or_else(|| field.get("default"));
        if let Some(value) = value {
            let kind = field["type"].as_str().unwrap_or("text");
            let valid = match kind {
                "boolean" => value.is_boolean(),
                "number" => value.as_f64().is_some_and(|number| {
                    number.is_finite()
                        && number >= field["min"].as_f64().unwrap_or(f64::NEG_INFINITY)
                        && number <= field["max"].as_f64().unwrap_or(f64::INFINITY)
                }),
                "select" => value.as_str().is_some_and(|text| {
                    field["choices"]
                        .as_array()
                        .is_some_and(|choices| choices.iter().any(|choice| choice["value"] == text))
                }),
                "text" | "password" => value.as_str().is_some_and(|text| text.len() <= 2048),
                _ => false,
            };
            if !valid {
                return Err(format!("Invalid {name} value"));
            }
            output.insert(name.to_owned(), value.clone());
        } else if field["required"] == true {
            return Err(format!("{name} is required"));
        }
    }
    Ok(Value::Object(output))
}
fn validate_snapshot(manifest: &Value, raw: &Value) -> Result<(), String> {
    if !raw.is_object() || serde_json::to_vec(raw).map_err(|e| e.to_string())?.len() > 60_000 {
        return Err("Extension poll must be a bounded object".into());
    }
    if let Some(states) = raw["states"].as_object() {
        if states.len() > 32
            || states
                .iter()
                .any(|(key, value)| !valid_key(key) || !value.is_boolean())
        {
            return Err("Invalid extension states".into());
        }
    }
    for group in ["sources", "dashboards"] {
        let Some(values) = raw[group].as_object() else {
            continue;
        };
        let declared: HashSet<_> = manifest[group]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|item| item["id"].as_str())
            .collect();
        if values.keys().any(|name| !declared.contains(name.as_str())) {
            return Err(format!("Undeclared {group}"));
        }
        for value in values.values() {
            if group == "sources" {
                let entries = value.as_array().ok_or("Source must be a list")?;
                if entries.len() > 32 {
                    return Err("Too many source entries".into());
                }
                let mut seen = HashSet::new();
                for entry in entries {
                    let id = entry["id"].as_str().ok_or("Source entry ID missing")?;
                    if !valid_key(id) || !seen.insert(id) {
                        return Err("Invalid or duplicate source entry".into());
                    }
                    if !localized_ok(&entry["label"], 64) || !localized_ok(&entry["detail"], 80) {
                        return Err("Source label or detail exceeds limit".into());
                    }
                    if !entry["icon"].as_str().is_some_and(|icon| icon.len() <= 16)
                        || !entry["color"].as_str().is_some_and(color_ok)
                        || !entry["active"].is_boolean()
                    {
                        return Err("Invalid source entry display fields".into());
                    }
                    let action = entry["action"]["id"]
                        .as_str()
                        .ok_or("Source action missing")?;
                    let spec = manifest["actions"]
                        .as_array()
                        .and_then(|items| items.iter().find(|item| item["id"] == action))
                        .ok_or("Source action undeclared")?;
                    validate_values(&spec["arguments"], &entry["action"]["arguments"])?;
                }
            } else {
                let cards = value["cards"].as_array().ok_or("Dashboard cards missing")?;
                if cards.len() > 4 || !localized_ok(&value["title"], 64) {
                    return Err("Invalid dashboard".into());
                }
                for card in cards {
                    if !localized_ok(&card["label"], 48)
                        || !card["value"].as_str().is_some_and(|text| text.len() <= 40)
                        || !localized_ok(&card["detail"], 80)
                    {
                        return Err("Invalid dashboard card".into());
                    }
                }
            }
        }
    }
    Ok(())
}
fn localized_ok(value: &Value, max: usize) -> bool {
    value.as_str().is_some_and(|text| text.len() <= max)
        || value["en"].as_str().is_some_and(|text| text.len() <= max)
}
fn color_ok(value: &str) -> bool {
    value.len() == 7
        && value.starts_with('#')
        && value[1..].bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn install_archive(archive: &Path, root: &Path) -> Result<String, String> {
    if archive.metadata().map_err(|e| e.to_string())?.len() > MAX_ARCHIVE {
        return Err("Archive exceeds 4 MiB".into());
    }
    let file = fs::File::open(archive).map_err(|e| e.to_string())?;
    let mut zip = zip::ZipArchive::new(file).map_err(|e| e.to_string())?;
    if zip.len() > MAX_FILES {
        return Err("Archive exceeds 256 entries".into());
    }
    let staging = root.join(format!(".install-{}", rand::random::<u64>()));
    fs::create_dir(&staging).map_err(|e| e.to_string())?;
    let outcome = (|| -> Result<String, String> {
        let mut names = HashSet::new();
        let mut total = 0u64;
        for index in 0..zip.len() {
            let mut entry = zip.by_index(index).map_err(|e| e.to_string())?;
            let name = entry.name().to_owned();
            let path = portable_path(name.trim_end_matches('/'))?;
            if !names.insert(name.to_ascii_lowercase()) {
                return Err("Duplicate package entry".into());
            }
            if entry.is_symlink() {
                return Err("Package symlink forbidden".into());
            }
            total += entry.size();
            if total > MAX_PACKAGE {
                return Err("Package exceeds 16 MiB".into());
            }
            let target = staging.join(path);
            if entry.is_dir() {
                fs::create_dir_all(target).map_err(|e| e.to_string())?;
            } else {
                fs::create_dir_all(target.parent().ok_or("Invalid package path")?)
                    .map_err(|e| e.to_string())?;
                let mut output = fs::File::create(&target).map_err(|e| e.to_string())?;
                std::io::copy(&mut (&mut entry).take(MAX_PACKAGE + 1), &mut output)
                    .map_err(|e| e.to_string())?;
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let mode = if entry.unix_mode().unwrap_or(0) & 0o111 != 0 {
                        0o700
                    } else {
                        0o600
                    };
                    fs::set_permissions(&target, fs::Permissions::from_mode(mode))
                        .map_err(|e| e.to_string())?;
                }
            }
        }
        let manifest = load_manifest(&staging)?;
        #[cfg(unix)]
        if let Some(path) = manifest["binaries"][target_key()].as_str() {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(staging.join(path), fs::Permissions::from_mode(0o700))
                .map_err(|e| e.to_string())?;
        }
        fingerprint(&staging)?;
        let id = manifest["id"]
            .as_str()
            .ok_or("Invalid package ID")?
            .to_owned();
        let dest = root.join("packages").join(&id);
        if dest.exists() {
            return Err("Already installed; remove old package before import".into());
        }
        fs::rename(&staging, dest).map_err(|e| e.to_string())?;
        Ok(id)
    })();
    if outcome.is_err() {
        let _ = fs::remove_dir_all(&staging);
    }
    outcome
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_manifest_and_references() {
        assert!(parse_reference("ext:com.example.timer/start").is_some());
        assert!(parse_reference("ext:../../etc/start").is_none());
        assert!(portable_path("bin/counter").is_ok());
        assert!(portable_path("../bin/counter").is_err());
        assert!(portable_path("CON.txt").is_err());
    }

    #[test]
    fn validates_typed_values() {
        let fields = json!([{"name":"count","type":"number","min":0,"max":5},{"name":"enabled","type":"boolean"}]);
        assert!(validate_values(&fields, &json!({"count":3,"enabled":true})).is_ok());
        assert!(validate_values(&fields, &json!({"count":7})).is_err());
    }

    #[test]
    fn accepts_only_packaged_native_binaries() {
        let root =
            std::env::temp_dir().join(format!("3decks-ext-manifest-{}", rand::random::<u64>()));
        fs::create_dir_all(root.join("bin")).unwrap();
        fs::write(root.join("bin/worker"), b"native").unwrap();
        let mut binaries = serde_json::Map::new();
        binaries.insert(target_key().into(), json!("bin/worker"));
        let mut manifest = json!({"api_version":1,"id":"com.example.native","version":"1.0.0",
            "name":{"en":"Native"},"description":{"en":"Test"},"author":"Example",
            "runtime":"native","binaries":binaries});
        let path = root.join("extension.json");
        fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
        assert_eq!(
            load_manifest(&root).unwrap()["platforms"],
            json!([platform()])
        );
        for runtime in ["python", "command"] {
            manifest["runtime"] = json!(runtime);
            fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
            assert!(load_manifest(&root).is_err());
        }
        manifest["runtime"] = json!("native");
        manifest["binaries"][target_key()] = json!("/usr/bin/true");
        fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
        assert!(load_manifest(&root).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[tokio::test]
    async fn native_sdk_worker_requires_digest_approval_and_handles_actions() {
        let Some(executable) = std::env::var_os("DECKS_TEST_NATIVE_EXTENSION") else {
            return;
        };
        let root = std::env::temp_dir().join(format!("3decks-ext-test-{}", rand::random::<u64>()));
        let package = root.join("packages/com.example.worker");
        fs::create_dir_all(package.join("bin")).unwrap();
        let binary_name = if cfg!(windows) {
            "counter.exe"
        } else {
            "counter"
        };
        fs::copy(executable, package.join("bin").join(binary_name)).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(
                package.join("bin").join(binary_name),
                fs::Permissions::from_mode(0o700),
            )
            .unwrap();
        }
        let mut binaries = serde_json::Map::new();
        binaries.insert(target_key().into(), json!(format!("bin/{binary_name}")));
        fs::write(package.join("extension.json"), serde_json::to_vec(&json!({
            "api_version":1,"id":"com.example.worker","version":"1.0.0",
            "name":{"en":"Worker","fr":"Worker"},"description":{"en":"Test worker","fr":"Test worker"},
            "author":"3Decks","runtime":"native","binaries":binaries,
            "actions":[{"id":"increment","title":{"en":"Increment","fr":"Incrémenter"},"arguments":[]}],
            "sources":[],"dashboards":[{"id":"overview","title":{"en":"Counter","fr":"Compteur"}}],"settings":[]
        })).unwrap()).unwrap();
        assert_eq!(
            load_manifest(&package).unwrap()["platforms"],
            json!([platform()])
        );
        let mut legacy = read_object(&package.join("extension.json")).unwrap();
        legacy["runtime"] = json!("python");
        fs::write(
            package.join("extension.json"),
            serde_json::to_vec(&legacy).unwrap(),
        )
        .unwrap();
        assert!(load_manifest(&package).is_err());
        legacy["runtime"] = json!("native");
        fs::write(
            package.join("extension.json"),
            serde_json::to_vec(&legacy).unwrap(),
        )
        .unwrap();
        let mut host = ExtensionHost::new(root.clone()).unwrap();
        let digest = host.packages["com.example.worker"].digest.clone();
        assert!(host.manage(json!({"operation":"enable","id":"com.example.worker","trust":true,"digest":"wrong"})).await.is_err());
        host.manage(
            json!({"operation":"enable","id":"com.example.worker","trust":true,"digest":digest}),
        )
        .await
        .unwrap();
        host.poll_all().await;
        assert_eq!(host.describe()["extensions"][0]["status"], "ready", "{}", host.describe());
        assert_eq!(
            host.execute("ext:com.example.worker/increment", &json!({}))
                .await
                .unwrap(),
            "Counter / Compteur: 1"
        );
        assert_eq!(
            host.snapshots()["com.example.worker"]["states"]["ready"],
            true
        );
        host.manage(json!({"operation":"disable","id":"com.example.worker"}))
            .await
            .unwrap();
        assert!(host
            .execute("ext:com.example.worker/increment", &json!({}))
            .await
            .is_err());
        fs::remove_dir_all(root).unwrap();
    }
}
