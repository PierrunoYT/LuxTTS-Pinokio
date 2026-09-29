import threading
import time
import torch
import numpy as np
import gradio as gr
from zipvoice.luxvoice import LuxTTS

DEFAULT_MODEL_PATH = "YatharthS/LuxTTS"
DEFAULT_THREADS = 2


def mps_available():
    """True only when this torch build actually ships a working MPS backend."""
    backend = getattr(torch.backends, "mps", None)
    if backend is None:
        return False
    try:
        return bool(backend.is_built() and backend.is_available())
    except Exception:
        return False


def default_device():
    if torch.cuda.is_available():
        return "cuda"
    if mps_available():
        return "mps"
    return "cpu"


# ---------------------------------------------------------------------------
# Model cache — a single slot keyed by (model_path, device, threads). Only one
# model is held at a time: keeping every combination the user tried would pin
# a full copy of the weights per device, which exhausts VRAM after a couple of
# switches. The lock keeps concurrent Gradio requests from loading twice.
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_cached = {"key": None, "model": None}


def get_model(model_path, device, threads):
    key = (model_path, device, int(threads))
    with _model_lock:
        if _cached["key"] != key:
            # Drop the previous model before allocating the next one.
            _cached["key"] = None
            _cached["model"] = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print(f"Loading LuxTTS model: {model_path}…")
            _cached["model"] = LuxTTS(model_path, device=device, threads=int(threads))
            _cached["key"] = key
            print("Model loaded successfully!")
        return _cached["model"]


def as_float(value, default):
    """Gradio hands back None when a Number field is cleared."""
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default):
    try:
        return default if value is None else int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def generate_speech(
    text,
    audio_prompt,
    model_path,
    device,
    threads,
    ref_duration,
    rms,
    num_steps,
    t_shift,
    speed,
    return_smooth,
):
    if not text:
        return None, "⚠️ Please enter text to synthesize."
    if audio_prompt is None:
        return None, "⚠️ Please upload a reference audio file."

    try:
        model = get_model(model_path, device, as_int(threads, DEFAULT_THREADS))

        start = time.time()

        encoded_prompt = model.encode_prompt(
            audio_prompt,
            duration=as_float(ref_duration, 5.0),
            rms=as_float(rms, 0.01),
        )

        final_wav = model.generate_speech(
            text,
            encoded_prompt,
            num_steps=as_int(num_steps, 4),
            t_shift=as_float(t_shift, 0.9),
            speed=as_float(speed, 0.8),
            return_smooth=bool(return_smooth),
        )

        elapsed = round(time.time() - start, 2)

        if isinstance(final_wav, torch.Tensor):
            final_wav = final_wav.detach().cpu().squeeze().numpy()
        else:
            final_wav = np.asarray(final_wav).squeeze()

        # squeeze() can collapse a single-sample result to a 0-d array, and an
        # empty result would make the peak computation below raise.
        final_wav = np.atleast_1d(np.asarray(final_wav, dtype=np.float32))
        if final_wav.size == 0:
            return None, "❌ The model returned no audio. Try a longer reference clip."

        # Normalise and convert to int16 — avoids Gradio silently clipping
        # a float32 array during its own auto-conversion.
        peak = np.abs(final_wav).max()
        if peak > 0:
            final_wav = final_wav / peak
        final_wav = (np.clip(final_wav, -1.0, 1.0) * 32767).astype(np.int16)

        sample_rate = 24000 if return_smooth else 48000

        return (sample_rate, final_wav), f"✨ Generated in **{elapsed}s** at {sample_rate} Hz."

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"❌ Error: {e}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
with gr.Blocks(title="LuxTTS 🎙️", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎙️ LuxTTS Voice Cloning")
    gr.Markdown(
        "High-quality rapid TTS — 150× realtime, 48 kHz speech generation.  \n"
        "> **Tip:** If words get cut off, lower **Speed** or increase **Ref Duration**."
    )

    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(
                label="Text to Synthesize",
                placeholder="Enter text here…",
                lines=3,
                value="Hey, what's up? I'm feeling really great!",
            )

            audio_prompt = gr.Audio(
                label="Reference Audio — min 3 s, WAV/MP3/FLAC",
                type="filepath",
            )

            with gr.Row():
                ref_duration = gr.Number(
                    label="Ref Duration (s)",
                    value=5,
                    info="Lower = faster. Set a large value (e.g. 1000) if you hear artifacts.",
                )
                rms = gr.Number(
                    label="RMS (Loudness)",
                    value=0.01,
                    info="0.01 recommended",
                )
                t_shift = gr.Number(
                    label="T-Shift",
                    value=0.9,
                    info="Higher = better quality but worse WER",
                )

            with gr.Row():
                num_steps = gr.Slider(
                    1, 10, value=4, step=1,
                    label="Sampling Steps",
                    info="3-4 is the sweet spot",
                )
                speed = gr.Slider(
                    0.5, 2.0, value=0.8, step=0.05,
                    label="Speed",
                    info="Lower = slower / clearer",
                )
                return_smooth = gr.Checkbox(
                    label="Return Smooth",
                    value=False,
                    info="Smoother output at 24 kHz instead of 48 kHz",
                )

            with gr.Accordion("Advanced Settings", open=False):
                model_path = gr.Textbox(
                    label="Model Path",
                    value=DEFAULT_MODEL_PATH,
                    info="Hugging Face repo ID or local path",
                )
                device_choices = ["cpu"]
                if torch.cuda.is_available():
                    device_choices.insert(0, "cuda")
                if mps_available():
                    device_choices.append("mps")
                device = gr.Radio(
                    label="Device",
                    choices=device_choices,
                    value=default_device() if default_device() in device_choices else device_choices[0],
                )
                # Threads only apply to the CPU (ONNX) path, so show the slider
                # only while cpu is selected.
                threads = gr.Slider(
                    1, 16, value=DEFAULT_THREADS, step=1,
                    label="CPU Threads",
                    visible=device.value == "cpu",
                )
                device.change(
                    fn=lambda d: gr.update(visible=d == "cpu"),
                    inputs=device,
                    outputs=threads,
                )

            generate_btn = gr.Button("Generate Speech 🎵", variant="primary")

        with gr.Column():
            audio_output = gr.Audio(label="Generated Audio")
            status_text = gr.Markdown("Ready to generate…")

    generate_btn.click(
        fn=generate_speech,
        api_name="generate_speech",
        inputs=[
            text_input,
            audio_prompt,
            model_path,
            device,
            threads,
            ref_duration,
            rms,
            num_steps,
            t_shift,
            speed,
            return_smooth,
        ],
        outputs=[audio_output, status_text],
    )

    # Only one generation runs at a time — the model slot below holds a single
    # instance, so parallel requests would fight over the same weights.
    demo.queue(default_concurrency_limit=1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LuxTTS Gradio Interface")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    print("Initializing LuxTTS model…")
    try:
        get_model(DEFAULT_MODEL_PATH, default_device(), DEFAULT_THREADS)
    except Exception as e:
        print(f"Warning: could not pre-load model: {e}")

    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=False,
    )
