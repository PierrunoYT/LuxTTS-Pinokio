import os
import time
import torch
import numpy as np
import gradio as gr
from zipvoice.luxvoice import LuxTTS

# ---------------------------------------------------------------------------
# Model cache — keyed by (model_path, device, threads) so the model is only
# reloaded when the user actually changes one of those settings.
# ---------------------------------------------------------------------------
loaded_models = {}


def get_model(model_path, device, threads):
    key = (model_path, device, int(threads))
    if key not in loaded_models:
        print(f"Loading LuxTTS model: {model_path}…")
        loaded_models[key] = LuxTTS(model_path, device=device, threads=int(threads))
        print("Model loaded successfully!")
    return loaded_models[key]


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
        model = get_model(model_path, device, threads)

        start = time.time()

        encoded_prompt = model.encode_prompt(
            audio_prompt,
            duration=float(ref_duration),
            rms=float(rms),
        )

        final_wav = model.generate_speech(
            text,
            encoded_prompt,
            num_steps=int(num_steps),
            t_shift=float(t_shift),
            speed=float(speed),
            return_smooth=bool(return_smooth),
        )

        elapsed = round(time.time() - start, 2)

        if isinstance(final_wav, torch.Tensor):
            final_wav = final_wav.detach().cpu().squeeze().numpy()
        else:
            final_wav = np.asarray(final_wav).squeeze()

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
                    value="YatharthS/LuxTTS",
                    info="Hugging Face repo ID or local path",
                )
                device = gr.Radio(
                    label="Device",
                    choices=["cuda", "cpu", "mps"] if torch.cuda.is_available() else ["cpu", "mps"],
                    value="cuda" if torch.cuda.is_available() else "cpu",
                )
                threads = gr.Slider(
                    1, 16, value=2, step=1,
                    label="CPU Threads",
                    visible=False,
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LuxTTS Gradio Interface")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    print("Initializing LuxTTS model…")
    try:
        get_model("YatharthS/LuxTTS", "cuda" if torch.cuda.is_available() else "cpu", 2)
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Warning: could not pre-load model: {e}")

    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=False,
    )
