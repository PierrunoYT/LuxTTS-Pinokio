module.exports = {
  run: [
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
        message: [
          "uv pip install -r requirements.txt",
          "uv pip install git+https://github.com/ysharma3501/LuxTTS.git --no-deps",
        ],
      },
    },
    {
      method: "input",
      params: {
        title: "Install Complete",
        description: "LuxTTS installed successfully. Click Start to launch the app.",
      },
    },
  ],
}
