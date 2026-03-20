module.exports = {
  daemon: true,
  run: [
    // Start LuxTTS Gradio interface
    {
      method: "shell.run",
      params: {
        venv: "env",
        env: { },
        message: [
          "python app.py",
        ],
        on: [{
          // Monitor for Gradio server URL
          "event": "/http:\\/\\/\\S+/",
          "done": true
        }]
      }
    },
    // Set the local URL for the "Open Web UI" tab
    {
      method: "local.set",
      params: {
        // Use the captured URL from the previous step
        url: "{{input.event[0]}}"
      }
    },
  ]
}
