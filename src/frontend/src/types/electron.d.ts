/** Type declarations for the Electron preload desktop API. */

export interface DesktopAPI {
  getApiConfig(): { baseUrl: string; token: string };
  onNotificationClick(callback: (conversationId: string) => void): void;
  onWindowFocus(callback: () => void): void;
  onMessagesChanged(callback: (conversationId: string) => void): void;
  setNotificationsEnabled(enabled: boolean): void;
  showWindow(): void;
}

declare global {
  interface Window {
    desktopAPI?: DesktopAPI;
  }
}

export {};
