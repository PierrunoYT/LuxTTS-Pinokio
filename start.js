module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "python -u app.py --port {{port}}",
        on: [{
          // Match Gradio's own banner rather than the first URL on stdout —
          // model downloads and version notices print URLs before the server
          // is up, and those would be captured as the Web UI link.
          event: "/Running on local URL:\\s+(https?:\\/\\/\\S+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    },
  ]
}
