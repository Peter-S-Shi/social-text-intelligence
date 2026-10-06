# PROTOTYPE — throwaway V2 desktop architecture spikes

These files answer questions for the V2 Desktop Architecture Exploration. They
are **not production code**, are not packaged, have no tests, and live only on
the `prototype/v2-desktop-spikes` branch. `main` keeps only the validated
decision, recorded in `docs/V2_DESKTOP_ARCHITECTURE_EXPLORATION.md`.

| Spike | File | Question |
| --- | --- | --- |
| A | `spike_a_native_shell.py` | Can a native Qt shell call the V1 analysis service in-process (no Flask/HTTP), off the UI thread, with real offline models? |
| A-wx | `spike_a_wx_shell.py` | Same question for wxPython, the strongest alternative toolkit |
| B | `spike_b_sqlite_store.py` | Persistence boundary: per-user data dir, schema, real delete, concurrency, crash safety |
| C | (PyInstaller commands in the decision record) | Packaging blockers and footprint |

They run from a scratch virtual environment that exposes the V1 source and
dependencies read-only; they do not change the project's dependencies. All
inputs are synthetic. Spike B writes only to a temporary directory and wipes it.
