# Backlog

## Bugs

- **`btoa` stack overflow on long recordings** — `sendAudio` in `index.html` does `btoa(String.fromCharCode(...new Uint8Array(buffer)))`, spreading the full audio array into function arguments. Hits the JS engine call-stack limit on recordings over a few seconds. Fix: encode in chunks or use a `FileReader`/`Blob` base64 approach.

- **Mic stream not released after recording** — `stopRecording` calls `mediaRecorder.stop()` but never calls `stream.getTracks().forEach(t => t.stop())`. The mic stays open (browser shows the recording indicator) between button presses.

- **`asyncio.create_task()` called from thread executor in `main_pi.py`** — `store_turn` calls `asyncio.create_task(run(memory.store, ...))` from inside `stream_sentences`, which runs in `loop.run_in_executor`. `create_task` requires a running event loop in the current thread and raises `RuntimeError` here. Fix: use `loop.call_soon_threadsafe` with a coroutine, or call `memory.store` directly (it's not async).

- **`MediaRecorder` MIME type hardcoded as `audio/webm`** — `sendAudio` constructs the `Blob` with `type: 'audio/webm'` regardless of what the browser actually recorded. Safari uses `audio/mp4`. Fix: use `mediaRecorder.mimeType` when constructing the `Blob`.

## Features

- **Chrome Kiosk Mode for dedicated device** — Launch the web app UI in Chrome kiosk mode (`--kiosk` flag) so the browser is locked to the app full-screen with no address bar, tabs, or menus. Add a launch script that runs `google-chrome --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:<port>`. Consider wiring it into a systemd unit or `.xinitrc` for auto-start on boot (Raspberry Pi).

## Refactoring

- **Deduplicate entry points** — `conversation_loop`, `say`, `run`, and `sanitize_for_speech` are copy-pasted between `main_mac.py` and `main_pi.py`. Extract shared logic into a module; entry points should only wire up hardware.

- **Hardware interfaces** — `Speaker`, `MacOSSpeaker`, `Listener`, `MacOSListener`, `Camera`, `MacOSCamera` have no base class or protocol. Define a minimal interface for each so platform swaps are safe and the compiler can catch mismatches.

- **Camera tool wiring** — `make_camera_tool` is appended to `CHILD_ROBOT_CONFIG.tools` manually in each entry point. Move this into the config definition so it's declared once.
