#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

use serde::Serialize;
use tauri::{Manager, State, WindowEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use uuid::Uuid;

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConfig {
    api_base: String,
    token: String,
}

struct BackendProcess(Mutex<Option<CommandChild>>);

#[tauri::command]
fn runtime_config(state: State<'_, RuntimeConfig>) -> RuntimeConfig {
    state.inner().clone()
}

fn main() {
    let token = Uuid::new_v4().to_string();
    let desktop_runtime = RuntimeConfig {
        api_base: "http://127.0.0.1:8765".to_string(),
        token: token.clone(),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(desktop_runtime)
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![runtime_config])
        .setup(move |app| {
            let data_dir = app.path().app_data_dir()?;
            std::fs::create_dir_all(&data_dir)?;

            let sidecar = app
                .shell()
                .sidecar("bubble-agent-backend")?
                .env("BUBBLE_AGENT_API_TOKEN", &token)
                .env("BUBBLE_AGENT_DATA_DIR", data_dir.to_string_lossy().to_string())
                .env("BUBBLE_AGENT_HOST", "127.0.0.1")
                .env("BUBBLE_AGENT_PORT", "8765");
            let (mut events, child) = sidecar.spawn()?;
            *app.state::<BackendProcess>().0.lock().expect("backend process lock") = Some(child);

            tauri::async_runtime::spawn(async move {
                while events.recv().await.is_some() {
                    // Drain sidecar output so its pipes never block. Application traces live in SQLite.
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::Destroyed) {
                let state = window.state::<BackendProcess>();
                let child = state.0.lock().expect("backend process lock").take();
                if let Some(child) = child {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Bubble Agent");
}
