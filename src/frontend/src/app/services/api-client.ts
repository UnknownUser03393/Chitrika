/** Shared authenticated transport for every renderer API module. */

const desktopApiConfig = window.desktopAPI?.getApiConfig?.();

export const API_BASE: string = desktopApiConfig?.baseUrl || "/api";
const API_TOKEN: string =
  desktopApiConfig?.token || import.meta.env.VITE_CHITRIKA_API_TOKEN || "";

export function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (API_TOKEN) headers.set("Authorization", `Bearer ${API_TOKEN}`);
  return globalThis.fetch(input, { ...init, headers });
}
