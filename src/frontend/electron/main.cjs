/**
 * Electron main process — window management, backend lifecycle,
 * toast worker, and desktop notification polling.
 */

const { app, BrowserWindow, ipcMain } = require("electron");
const { join } = require("path");
const { spawn } = require("child_process");
const { startBackend, stopBackend } = require("./backend.cjs");

const BACKEND_PORT = 8000;
const isDev = !app.isPackaged;

let mainWindow = null;
let toastWorker = null;
let notificationPollTimer = null;
let notificationsEnabled = true;
const notifiedMessageIds = new Set();

// ---------------------------------------------------------------------------
// Window creation
// ---------------------------------------------------------------------------

function createWindow() {
  const win = new BrowserWindow({
    width: 960,
    height: 680,
    minWidth: 640,
    minHeight: 400,
    title: "Chitrika Desktop",
    backgroundColor: "#0E1621",
    show: false,
    webPreferences: {
      preload: join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.once("ready-to-show", () => {
    win.show();
  });

  win.on("focus", () => {
    win.webContents.send("window-focus");
  });

  if (isDev) {
    win.loadURL("http://127.0.0.1:8080");
  } else {
    win.loadFile(join(__dirname, "..", "dist", "index.html"));
  }

  return win;
}

// ---------------------------------------------------------------------------
// Toast worker
// ---------------------------------------------------------------------------

function startToastWorker() {
  const script = join(__dirname, "..", "..", "..", "src", "chitrika", "services", "toast_worker.py");

  toastWorker = spawn("python", [script], {
    stdio: ["pipe", "pipe", "pipe"],
  });

  toastWorker.stdout.on("data", (data) => {
    for (const line of data.toString().split("\n")) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.type === "shown" && msg.message_id) {
          ackNotification(msg.message_id);
        }
      } catch { /* skip malformed lines */ }
    }
  });

  toastWorker.stderr.on("data", (data) => {
    process.stderr.write(`[toast-worker] ${data}`);
  });

  toastWorker.on("exit", (code) => {
    if (code !== 0) {
      console.error(`Toast worker exited with code ${code}`);
    }
    toastWorker = null;
  });
}

function sendToast(title, content, messageId) {
  if (!toastWorker || toastWorker.killed) return;

  const request = JSON.stringify({
    type: "notify",
    title,
    content,
    message_id: messageId,
  }) + "\n";

  toastWorker.stdin.write(request);
}

function stopToastWorker() {
  if (toastWorker && !toastWorker.killed) {
    toastWorker.stdin.write(JSON.stringify({ type: "quit" }) + "\n");
    setTimeout(() => {
      if (toastWorker && !toastWorker.killed) {
        toastWorker.kill();
      }
    }, 3000);
  }
}

// ---------------------------------------------------------------------------
// Notification polling
// ---------------------------------------------------------------------------

async function pollNotifications() {
  if (!notificationsEnabled) return;

  try {
    const url = `http://127.0.0.1:${BACKEND_PORT}/api/desktop/notifications/pending`;
    const res = await fetch(url);
    if (!res.ok) return;

    const pending = await res.json();

    for (const item of pending) {
      if (notifiedMessageIds.has(item.message_id)) continue;

      notifiedMessageIds.add(item.message_id);

      // Only show if window is not focused
      if (mainWindow && mainWindow.isFocused()) {
        ackNotification(item.message_id);
        continue;
      }

      const content = item.content_preview.length > 100
        ? item.content_preview.slice(0, 100) + "..."
        : item.content_preview;

      sendToast("Chitrika", content, item.message_id);
    }
  } catch {
    // Backend may not be up yet — retry next poll
  }
}

async function ackNotification(messageId) {
  try {
    await fetch(
      `http://127.0.0.1:${BACKEND_PORT}/api/desktop/notifications/${messageId}/ack`,
      { method: "POST" },
    );
  } catch { /* retry next poll */ }
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

function setupIPC() {
  ipcMain.on("get-api-base", (event) => {
    event.returnValue = `http://127.0.0.1:${BACKEND_PORT}/api`;
  });

  ipcMain.on("show-window", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  ipcMain.on("set-notifications-enabled", (_event, enabled) => {
    notificationsEnabled = enabled;
  });
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(async () => {
  setupIPC();

  // Start backend (in dev, user starts it manually)
  if (!isDev) {
    try {
      await startBackend(BACKEND_PORT);
      console.log("Backend started");
    } catch (err) {
      console.error("Backend start failed:", err);
    }
  }

  // Start toast worker
  startToastWorker();

  // Create window
  mainWindow = createWindow();

  // Start notification polling
  notificationPollTimer = setInterval(pollNotifications, 15_000);
  setTimeout(pollNotifications, 5_000);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (notificationPollTimer) {
    clearInterval(notificationPollTimer);
    notificationPollTimer = null;
  }
  stopToastWorker();
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (notificationPollTimer) {
    clearInterval(notificationPollTimer);
  }
  stopToastWorker();
  stopBackend();
});
