/**
 * Python backend lifecycle manager — CommonJS.
 *
 * Dev: spawns `uv run uvicorn` from the repo root.
 * Packaged: spawns the PyInstaller-built backend.exe from resources/ and
 * points it at a per-user data dir (db, plugins, logs) so the install dir
 * stays read-only. Prepares that data dir on first launch.
 */

const { app } = require("electron");
const { spawn } = require("child_process");
const { join } = require("path");
const fs = require("fs");
const http = require("http");

let backendProcess = null;

function isChitrikaHealth(body) {
  try {
    const payload = JSON.parse(body);
    return payload?.service === "chitrika" && payload?.ready === true;
  } catch {
    return false;
  }
}

/** Resolve the project root (where pyproject.toml lives). */
function projectRoot() {
  return join(__dirname, "..", "..", "..");
}

/**
 * Create the writable data directory (%APPDATA%/Chitrika) and seed bundled
 * resources into it on first run. Returns the data dir path.
 */
async function prepareDataDir() {
  const dataDir = app.getPath("userData");
  fs.mkdirSync(join(dataDir, "plugins"), { recursive: true });
  fs.mkdirSync(join(dataDir, "logs"), { recursive: true });

  // Seed the bundled deepseek_local plugin + skill file the first time.
  const seed = join(process.resourcesPath, "seed");
  if (fs.existsSync(seed)) {
    const srcPlugin = join(seed, "plugins", "deepseek_local");
    const dstPlugin = join(dataDir, "plugins", "deepseek_local");
    if (fs.existsSync(srcPlugin) && !fs.existsSync(dstPlugin)) {
      fs.cpSync(srcPlugin, dstPlugin, { recursive: true });
    }
  }
  return dataDir;
}

/**
 * Start the Python backend and return a promise that resolves when healthy.
 * opts: { packaged, dataDir, resourcesDir }
 */
function startBackend(port, opts = {}) {
  const { packaged = false, dataDir = null, resourcesDir = null, apiToken = "" } = opts;

  return new Promise((resolve, reject) => {
    let cmd;
    let args;
    let cwd;
    const env = {
      ...process.env,
      CHITRIKA_PORT: String(port),
      CHITRIKA_API_TOKEN: apiToken,
      CORS_ORIGINS: packaged ? "null" : "http://127.0.0.1:8080,http://localhost:8080",
    };

    if (packaged) {
      cmd = join(resourcesDir, "backend", "backend.exe");
      args = [];
      cwd = dataDir;
      env.DATABASE_URL = `sqlite:///${dataDir.replace(/\\/g, "/")}/chitrika.db`;
      env.PLUGINS_DIR = join(dataDir, "plugins");
      env.CHITRIKA_LOG_DIR = join(dataDir, "logs");
      env.CHITRIKA_SKILL_FILE = join(resourcesDir, "seed", "skill_0624.txt");
      env.EMOTION_CLASSIFIER_MODEL_DIR = join(resourcesDir, "models", "emotion");
      env.EMBEDDING_MODEL_DIR = join(resourcesDir, "models", "embedding");
    } else {
      cmd = "uv";
      args = ["run", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", String(port)];
      cwd = projectRoot();
    }

    backendProcess = spawn(cmd, args, {
      cwd,
      env,
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
    const timeout = Date.now() + 60_000;
    const poll = () => {
      if (Date.now() > timeout) {
        reject(new Error("Backend startup timed out"));
        return;
      }

      http.get(`http://127.0.0.1:${port}/api/health`, {
        headers: { Authorization: `Bearer ${apiToken}` },
      }, (res) => {
        res.setEncoding("utf8");
        let body = "";
        res.on("data", (chunk) => {
          if (body.length < 16_384) body += chunk;
        });
        res.on("end", () => {
          if (res.statusCode === 200 && isChitrikaHealth(body)) {
            resolve();
          } else if (res.statusCode === 200) {
            reject(new Error(
              `Port ${port} is occupied by a service that is not Chitrika`,
            ));
          } else {
            setTimeout(poll, 500);
          }
        });
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

module.exports = { startBackend, stopBackend, prepareDataDir, isChitrikaHealth };
