import os
import gradio as gr
import soundfile as sf
from zipvoice.luxvoice import LuxTTS
import numpy as np
import tempfile
import torch
import torchaudio

PROMPT_SR = 48000  # Sample rate LuxTTS expects for reference audio

# Model cache
loaded_models = {}


def get_model(model_path, device, threads):
    model_key = (model_path, device, int(threads))
    if model_key not in loaded_models:
        print(f"Loading LuxTTS model: {model_path}...")
        loaded_models[model_key] = LuxTTS(
            model_path, device=device, threads=int(threads)
        )
        print(f"Model loaded successfully!")
    return loaded_models[model_key]


def generate_speech(
    text,
    prompt_file,
    model_path,
    device,
    threads,
    prompt_duration,
    prompt_rms,
    num_steps,
    t_shift,
    speed,
    return_smooth,
):
    try:
        model = get_model(model_path, device, threads)

        # Load the uploaded prompt file
        temp_prompt = None
        try:
            if prompt_file is not None:
                # Read the audio file
                audio_data, sr = sf.read(prompt_file)

                # Convert to mono if stereo
                if audio_data.ndim > 1:
                    audio_data = np.mean(audio_data, axis=1)

                # Normalize if needed
                if np.issubdtype(audio_data.dtype, np.integer):
                    audio_data = (
                        audio_data.astype(np.float32) / np.iinfo(audio_data.dtype).max
                    )
                else:
                    audio_data = audio_data.astype(np.float32)

                # Resample to the rate LuxTTS expects for prompt encoding
                if sr != PROMPT_SR:
                    audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
                    audio_data = torchaudio.functional.resample(
                        audio_tensor, sr, PROMPT_SR
                    ).squeeze(0).numpy()
                    sr = PROMPT_SR

                # Create temp file if needed
                if prompt_file.endswith(".wav") or prompt_file.endswith(".flac"):
                    prompt_path = prompt_file
                else:
                    temp_prompt = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".wav"
                    )
                    prompt_path = temp_prompt.name
                    temp_prompt.close()
                    sf.write(prompt_path, audio_data, sr)
            else:
                raise gr.Error(
                    "Please upload a reference audio file for voice cloning."
                )

            # Encode prompt
            encoded_prompt = model.encode_prompt(
                prompt_path, duration=float(prompt_duration), rms=float(prompt_rms)
            )

            # Generate speech
            final_wav = model.generate_speech(
                text,
                encoded_prompt,
                num_steps=int(num_steps),
                t_shift=float(t_shift),
                speed=float(speed),
                return_smooth=bool(return_smooth),
            )

            # Convert to numpy if tensor
            if isinstance(final_wav, torch.Tensor):
                final_wav = final_wav.detach().cpu().numpy()

            final_wav = np.asarray(final_wav).squeeze()

            # Return numpy array directly to avoid Gradio file-serving Content-Length issues
            sample_rate = 24000 if return_smooth else 48000

            return (
                (sample_rate, final_wav),
                f"Audio generated successfully! Sample rate: {sample_rate}Hz",
            )
        finally:
            if temp_prompt and os.path.exists(temp_prompt.name):
                os.remove(temp_prompt.name)

    except Exception as e:
        import traceback

        traceback.print_exc()
        return None, f"Error generating audio: {str(e)}"


# Create Gradio interface
with gr.Blocks(title="LuxTTS 🎙️") as demo:
    gr.Markdown("# LuxTTS 🎙️")
    gr.Markdown(
        "High-quality rapid TTS voice cloning model - 150x+ realtime, 48kHz speech generation"
    )

    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(
                label="Text to synthesize",
                placeholder="Enter text here...",
                lines=3,
                value="Hey, what's up? I'm feeling really great if you ask me honestly!",
            )

            prompt_file = gr.Audio(
                label="Reference Audio (for voice cloning) — min 3 s, WAV/MP3/FLAC",
                type="filepath",
            )

            with gr.Accordion("Advanced Settings", open=False):
                model_path = gr.Textbox(
                    label="Model Path",
                    value="YatharthS/LuxTTS",
                    info="Hugging Face model path or local path",
                )

                device = gr.Radio(
                    label="Device",
                    choices=["cuda", "cpu", "mps"]
                    if torch.cuda.is_available()
                    else ["cpu", "mps"],
                    value="cuda" if torch.cuda.is_available() else "cpu",
                    info="Device to run inference on",
                )

                threads = gr.Slider(
                    label="CPU Threads",
                    minimum=1,
                    maximum=16,
                    step=1,
                    value=2,
                    visible=False,
                )

                prompt_duration = gr.Slider(
                    label="Prompt Duration (s)",
                    minimum=1,
                    maximum=20,
                    step=0.5,
                    value=5,
                    info="Set lower to speed up inference. If you hear artifacts, try setting this to the maximum.",
                )

                prompt_rms = gr.Slider(
                    label="Prompt RMS",
                    minimum=0.0,
                    maximum=0.05,
                    step=0.001,
                    value=0.01,
                    info="Higher makes it sound louder (0.01 recommended)",
                )

                num_steps = gr.Slider(
                    label="Sampling Steps",
                    minimum=1,
                    maximum=10,
                    step=1,
                    value=4,
                    info="Higher sounds better but takes longer (3-4 is best)",
                )

                t_shift = gr.Slider(
                    label="t_shift (sampling)",
                    minimum=0.3,
                    maximum=1.0,
                    step=0.05,
                    value=0.9,
                    info="Higher can sound better but worse WER",
                )

                speed = gr.Slider(
                    label="Speed",
                    minimum=0.5,
                    maximum=1.5,
                    step=0.05,
                    value=1.0,
                    info="Controls audio speed",
                )

                return_smooth = gr.Checkbox(
                    label="Return Smooth",
                    value=False,
                    info="Makes audio smoother but less clean",
                )

            generate_btn = gr.Button("Generate Speech 🎵", variant="primary")

        with gr.Column():
            audio_output = gr.Audio(label="Generated Audio")
            status_text = gr.Textbox(label="Status", interactive=False)

    gr.Examples(
        examples=[
            [
                "Hello world! This is LuxTTS speaking.",
                "audio_file.wav",
                "YatharthS/LuxTTS",
                5,
                0.01,
                4,
                0.9,
                1.0,
                False,
            ],
            [
                "The quick brown fox jumps over the lazy dog.",
                "audio_file.wav",
                "YatharthS/LuxTTS",
                5,
                0.01,
                4,
                0.9,
                1.0,
                False,
            ],
            [
                "LuxTTS is a high-quality voice cloning model that runs extremely fast.",
                "audio_file.wav",
                "YatharthS/LuxTTS",
                5,
                0.01,
                4,
                0.9,
                1.0,
                False,
            ],
        ],
        inputs=[
            text_input,
            prompt_file,
            model_path,
            prompt_duration,
            prompt_rms,
            num_steps,
            t_shift,
            speed,
            return_smooth,
        ],
    )

    generate_btn.click(
        fn=generate_speech,
        inputs=[
            text_input,
            prompt_file,
            model_path,
            device,
            threads,
            prompt_duration,
            prompt_rms,
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
    parser.add_argument(
        "--port", type=int, default=7860, help="Port to run the server on"
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to run the server on"
    )

    args = parser.parse_args()

    print("Initializing LuxTTS model...")
    try:
        get_model(
            "YatharthS/LuxTTS", "cpu" if not torch.cuda.is_available() else "cuda", 2
        )
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Warning: Could not pre-load model: {e}")

    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=False,
        theme=gr.themes.Default(),
    )
