module.exports = {
  daemon: true,
  run: [
    // Start LuxTTS Gradio interface
    {
      method: "shell.run",
      params: {
        venv: "env",
        env: { PYTHONUNBUFFERED: "1" },
        message: [
          "python -u app.py 2>&1",
        ],
        on: [{
          // Capture full http(s) URL for local.set (group 1 per Pinokio / Gepeto pattern)
          "event": "/(https?:\\/\\/\\S+)/",
          "done": true
        }]
      }
    },
    // Set the local URL for the "Open Web UI" tab
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    },
  ]
}
