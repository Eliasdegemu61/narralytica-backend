export async function fetchJson<T>(
  url: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
  return await response.json() as T;
}

export function buildUrl(url: string, params?: Record<string, string | number | undefined>) {
  const full = new URL(url);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        full.searchParams.set(key, String(value));
      }
    }
  }
  return full.toString();
}

