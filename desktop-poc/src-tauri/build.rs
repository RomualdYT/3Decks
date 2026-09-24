fn main() {
    let project = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("Tauri project directory");
    for file in ["catalog.json", "default-config.json"] {
        let path = project.join(file);
        println!("cargo:rerun-if-changed={}", path.display());
        let bytes = std::fs::read(&path)
            .unwrap_or_else(|error| panic!("Cannot read bundled {file}: {error}"));
        serde_json::from_slice::<serde_json::Value>(&bytes)
            .unwrap_or_else(|error| panic!("Bundled {file} is not valid JSON: {error}"));
    }
    tauri_build::build()
}
