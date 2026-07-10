/**
 * Python backend lifecycle manager — CommonJS.
 *
 * Starts the FastAPI server as a child process, waits for health check,
 * and kills it on app quit.
 */

const { spawn } = require("child_process");
const { join } = require("path");
const http = require("http");

let backendProcess = null;

/** Resolve the project root (where pyproject.toml lives). */
function projectRoot() {
  return join(__dirname, "..", "..", "..");
}

/** Start the Python backend and return a promise that resolves when healthy. */
function startBackend(port) {
  return new Promise((resolve, reject) => {
    const root = projectRoot();
    const cmd = "uv";
    const args = [
      "run",
      "uvicorn",
      "src.main:app",
      "--host", "127.0.0.1",
      "--port", String(port),
    ];

    backendProcess = spawn(cmd, args, {
      cwd: root,
      stdio: ["ignore", "pipe", "pipe"],
    });

    backendProcess.stdout.on("data", (data) => {
      process.stdout.write(`[backend] ${data}`);
    });

    backendProcess.stderr.on("data", (data) => {
      process.stderr.write(`[backend] ${data}`);
    });

    backendProcess.on("error", (err) => {
      reject(new Error(`Failed to start backend: ${err.message}`));
    });

    backendProcess.on("exit", (code) => {
      if (code !== 0 && code !== null) {
        console.error(`Backend exited with code ${code}`);
      }
      backendProcess = null;
    });

    // Poll health check until ready
    const timeout = Date.now() + 30_000;
    const poll = () => {
      if (Date.now() > timeout) {
        reject(new Error("Backend startup timed out"));
        return;
      }

      http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          setTimeout(poll, 500);
        }
      }).on("error", () => {
        setTimeout(poll, 500);
      });
    };

    setTimeout(poll, 1000);
  });
}

/** Kill the backend process. */
function stopBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill("SIGTERM");
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        backendProcess.kill("SIGKILL");
      }
    }, 5000);
  }
}

module.exports = { startBackend, stopBackend };
