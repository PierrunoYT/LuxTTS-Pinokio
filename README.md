# LuxTTS (Pinokio)

Pinokio launcher for [LuxTTS](https://github.com/ysharma3501/LuxTTS): fast voice cloning TTS with a Gradio web UI (`app.py`).

## What it does

- **Install** — Creates the Python virtualenv (`env`), installs dependencies with `uv`, runs `torch.js` for PyTorch on your platform, and verifies the LuxTTS import.
- **Start** — Runs `python -u app.py` and opens the Gradio URL in Pinokio when the server prints it.
- **Update** — `git pull` and `uv pip install -r requirements.txt`.
- **Reset** — Removes `env` and `INSTALLATION_COMPLETE.txt` so you can reinstall cleanly.
- **Save disk space** — Runs `fs.link` to deduplicate libraries in the venv (see Pinokio `link.js`).

Place an **`icon.jpg`** in the project root if you want the sidebar icon to load (see `pinokio.js`).

## How to use (Pinokio)

1. Open this project in Pinokio.
2. Click **Install**, wait for it to finish.
3. Click **Start**; use **Open Web UI** when it appears, or open the URL shown in the terminal.

Default server bind is **`127.0.0.1`** and port **`7860`** (see `app.py` arguments).

## Programmatic API (Gradio)

After **Start**, the app listens on the same URL Pinokio shows (for example `http://127.0.0.1:7860`). Gradio exposes a named endpoint **`generate_speech`** for the main Generate button.

### Python (`gradio_client`)

```python
from gradio_client import Client

base = "http://127.0.0.1:7860"  # use the URL from Pinokio / terminal
client = Client(base)

# Argument order matches the UI: text, reference audio path, model path, device, threads,
# prompt_duration, prompt_rms, num_steps, t_shift, speed, return_smooth
result = client.predict(
    "Hello from LuxTTS.",
    "/path/to/reference.wav",
    "YatharthS/LuxTTS",
    "cuda",  # or "cpu" / "mps"
    2,
    5,
    0.01,
    4,
    0.9,
    1.0,
    False,
    api_name="/generate_speech",
)
# result is typically (path_to_output_audio, status_string)
print(result)
```

Install the client in your own environment: `uv pip install gradio_client` (or `pip`).

### JavaScript

Use the **“Use via API”** section in the running Gradio UI footer to copy a ready-made `fetch` snippet for your Gradio version, or open:

`http://127.0.0.1:7860/?view=api` (path may vary slightly by Gradio version).

### cURL

Gradio expects JSON POST bodies that match its `/gradio_api/` schema. The most reliable approach is to copy the **curl** example from the Gradio **API** view in the running app so headers and payload match your Gradio version.

## Repository layout

- Launcher scripts: `install.js`, `start.js`, `update.js`, `reset.js`, `link.js`, `torch.js`, `pinokio.js`
- App entry: `app.py` (at repo root for this launcher)
