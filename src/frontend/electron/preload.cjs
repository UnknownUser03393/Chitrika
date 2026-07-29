/**
 * Electron preload script — exposes a narrow desktop API to the renderer
 * via contextBridge. The renderer never gets direct Node.js access.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopAPI", {
  /** Backend base URL for API calls (e.g. "http://127.0.0.1:8000/api"). */
  getApiBase: () => ipcRenderer.sendSync("get-api-base"),

  /** Listen for toast-click → switch-conversation events from main. */
  onNotificationClick: (callback) => {
    ipcRenderer.on("notification-click", (_event, conversationId) => {
      callback(conversationId);
    });
  },

  /** Listen for window focus events. */
  onWindowFocus: (callback) => {
    ipcRenderer.on("window-focus", () => callback());
  },

  /** Listen for messages created outside the active renderer chat stream. */
  onMessagesChanged: (callback) => {
    ipcRenderer.on("messages-changed", (_event, conversationId) => {
      callback(conversationId);
    });
  },

  /** Sync notification preference to main process. */
  setNotificationsEnabled: (enabled) => {
    ipcRenderer.send("set-notifications-enabled", enabled);
  },

  /** Request the main process to show the window. */
  showWindow: () => ipcRenderer.send("show-window"),
});
