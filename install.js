module.exports = {
  requires: {
    bundle: "ai"
  },
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "python -c \"from pathlib import Path; Path('env/.installed').unlink(missing_ok=True)\"",
          "uv pip install -r requirements.txt",
          "uv pip install git+https://github.com/ysharma3501/LuxTTS.git --no-deps",
        ],
      },
    },
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app",
        },
      },
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "python -c \"import torch, torchaudio, numpy, gradio, soundfile; from zipvoice.luxvoice import LuxTTS; from pathlib import Path; Path('env/.installed').touch(); print('LuxTTS dependencies verified.')\"",
      },
    },
    {
      when: "{{exists('app/env/.installed')}}",
      method: "input",
      params: {
        title: "Install Complete",
        description: "LuxTTS installed successfully. Click Start to launch the app.",
      },
    },
  ],
}
