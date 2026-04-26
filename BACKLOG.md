# Backlog

## Bugs

- **`asyncio.create_task()` called from thread executor in `main_pi.py`** — `store_turn` calls `asyncio.create_task(run(memory.store, ...))` from inside `stream_sentences`, which runs in `loop.run_in_executor`. `create_task` requires a running event loop in the current thread and raises `RuntimeError` here. Fix: call `memory.store` directly (it's not async) or use `loop.call_soon_threadsafe`.

## Features

- **Chrome Kiosk Mode for dedicated device** — Launch the web app UI in Chrome kiosk mode (`--kiosk` flag) so the browser is locked to the app full-screen with no address bar, tabs, or menus. Add a launch script that runs `google-chrome --kiosk --noerrdialogs --disable-infobars --no-first-run http://localhost:<port>`. Consider wiring it into a systemd unit or `.xinitrc` for auto-start on boot (Raspberry Pi).

## Refactoring

- **Hardware interfaces** — `Speaker`, `MacOSSpeaker`, `Listener`, `MacOSListener`, `Camera`, `MacOSCamera` have no base class or protocol. Define a minimal interface for each so platform swaps are safe and the compiler can catch mismatches.

- **Camera tool wiring in `main_pi.py`** — `make_camera_tool` is appended to `CHILD_ROBOT_CONFIG.tools` manually in `main_pi.py`'s `main()`. Move this into the config definition so it's declared once (the Mac path already handles this in `create_app`).
