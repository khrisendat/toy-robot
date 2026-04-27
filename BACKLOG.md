# Backlog

## Bugs

- **`asyncio.create_task()` called from thread executor in `main_pi.py`** — `store_turn` calls `asyncio.create_task(run(memory.store, ...))` from inside `stream_sentences`, which runs in `loop.run_in_executor`. `create_task` requires a running event loop in the current thread and raises `RuntimeError` here. Fix: call `memory.store` directly (it's not async) or use `loop.call_soon_threadsafe`.

- **Memory matrix/entries index mismatch in `src/lib/memory.py`** — `_rebuild_matrix` silently skips NaN embeddings, so the matrix row count can diverge from `_entries` length. A search returning row index N from the matrix may map to the wrong entry. Fix: track valid indices separately or filter `_entries` during rebuild.

- **Unguarded `json.loads` in `src/hardware/wake_word.py`** — Vosk result parsing calls `json.loads()` without try/except. Corrupted Vosk output crashes wake word detection hard with no recovery. Fix: wrap in try/except, default to empty string on failure.

- **`websocket.send_json()` unguarded in `src/server.py`** — Every send call is unprotected. A mid-response client disconnect raises an exception that bypasses the `WebSocketDisconnect` handler (which only catches clean disconnects). Fix: wrap sends in try/except or use a helper.

- **No WebSocket reconnect in browser** — If the server restarts or the connection drops, the browser goes dark permanently until the page is reloaded. Fix: implement exponential backoff reconnect in `static/index.html`.

## Features

- **Push-to-talk should cancel in-flight response** — If the robot is speaking and Kabir presses Hold to Talk, `_handle_audio` is still running and streaming audio. The server is in `busy` state so the push_to_talk message is dropped. Fix: track the in-flight asyncio task and cancel it on push_to_talk.

- **Recency bias in episodic memory** — Episodic search uses cosine similarity only; a memory from 6 months ago ranks equally with one from yesterday. Fix: boost score by recency (e.g., exponential decay on timestamp delta) when ranking results.

- **Chrome Kiosk Mode for dedicated device** — Launch the web app UI in Chrome kiosk mode (`--kiosk` flag) so the browser is locked to the app full-screen with no address bar, tabs, or menus. Add a launch script that runs `google-chrome --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:<port>`. Consider wiring it into a systemd unit or `.xinitrc` for auto-start on boot (Raspberry Pi).

- **Make follow-up window duration configurable** — 90 seconds is hardcoded in `server.py`. Move to an environment variable or config value.

## Refactoring

- **Hardware interfaces** — `Speaker`, `MacOSSpeaker`, `Listener`, `MacOSListener`, `Camera`, `MacOSCamera` have no base class or protocol. Define a minimal interface for each so platform swaps are safe and the compiler can catch mismatches.

- **Camera tool wiring in `main_pi.py`** — `make_camera_tool` is appended to `CHILD_ROBOT_CONFIG.tools` manually in `main_pi.py`'s `main()`. Move this into the config definition so it's declared once (the Mac path already handles this in `create_app`).
