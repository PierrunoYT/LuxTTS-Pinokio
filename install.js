module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "uv pip install -r requirements.txt",
        ],
      },
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "uv pip install git+https://github.com/ysharma3501/LuxTTS.git --no-deps",
      },
    },
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: ".",
        },
      },
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python -c \"from zipvoice.luxvoice import LuxTTS; print('LuxTTS installed successfully!')\"",
      },
    },
    {
      method: "fs.write",
      params: {
        path: "INSTALLATION_COMPLETE.txt",
        text: "LuxTTS 🎙️ installation completed successfully.\n\nNext steps:\n1. Start the application using the Start button\n2. Open the web interface at the provided URL\n3. Upload a reference audio file and begin generating speech with the high-quality voice cloning model\n\nFeatures:\n- 150x+ realtime speed\n- 48kHz clear speech generation\n- Voice cloning with reference audio\n- CPU/GPU/MPS support\n- Fits in 1GB VRAM\n\nFor support, visit: https://github.com/ysharma3501/LuxTTS",
      },
    },
  ],
}
