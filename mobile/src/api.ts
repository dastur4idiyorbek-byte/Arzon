/**
 * ARZON backend (FastAPI + Neon) bilan REST orqali ishlash.
 *
 * Backend O'ZGARMAYDI — bu native ilova undan API orqali foydalanadi.
 * Autentifikatsiya (JWT) 2-bosqichда qo'shiladi: token shu yerда saqlanadi
 * va har so'rovга `Authorization: Bearer <token>` qo'shiladi.
 */
import Constants from "expo-constants";

export const API_URL: string =
  (Constants.expoConfig?.extra?.apiUrl as string) ||
  "https://arzon-backend.onrender.com";

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Fayl yuklash (multipart) uchun — Content-Type'ni fetch o'zi qo'yishi kerak. */
export function authHeader(): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

export type ApiResult<T> = { ok: boolean; status: number; data: T | null };

export async function api<T = any>(
  path: string,
  opts: { method?: string; body?: unknown } = {}
): Promise<ApiResult<T>> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  try {
    const res = await fetch(API_URL + path, {
      method: opts.method || "GET",
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    let data: T | null = null;
    try {
      data = (await res.json()) as T;
    } catch {
      data = null;
    }
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

export function money(n: number | string): string {
  return Number(n).toLocaleString("en-US");
}
