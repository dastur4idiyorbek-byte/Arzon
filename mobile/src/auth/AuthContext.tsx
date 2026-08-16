/**
 * Autentifikatsiya konteksti — JWT tokenни xavfsiz saqlaydi (SecureStore),
 * har so'rovга qo'shadi va foydalanuvchi rolларини beradi.
 */
import React, { createContext, useContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";
import { api, setAuthToken } from "../api";
import { registerPush, unregisterPush } from "../push";

const TOKEN_KEY = "arzon_token";

export type AuthUser = {
  id: number;
  /** ARZON ID — foydalanuvchining yagona raqami (kirish usulidan qat'i nazar). */
  arzon_id: number;
  ism: string | null;
  email: string | null;
  tel: string | null;
  telegram_id: number | null;
  coin_balans: number;
};

type AuthState = {
  loading: boolean;
  user: AuthUser | null;
  roles: string[];
  signInWithToken: (token: string, user: AuthUser, roles: string[]) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthState>({} as AuthState);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [roles, setRoles] = useState<string[]>([]);

  async function loadFromToken(token: string) {
    setAuthToken(token);
    const { ok, data } = await api<{ user: AuthUser; roles: string[] }>("/api/auth/me");
    if (ok && data) {
      setUser(data.user);
      setRoles(data.roles);
      registerPush(); // push tokenини backendга yozamiz (Phase 5)
    } else {
      await signOut();
    }
  }

  useEffect(() => {
    (async () => {
      const token = await SecureStore.getItemAsync(TOKEN_KEY);
      if (token) await loadFromToken(token);
      setLoading(false);
    })();
  }, []);

  async function signInWithToken(token: string, u: AuthUser, r: string[]) {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    setAuthToken(token);
    setUser(u);
    setRoles(r);
    registerPush(); // push tokenини backendга yozamiz (Phase 5)
  }

  async function signOut() {
    await unregisterPush(); // token hali borда o'chiramiz
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setAuthToken(null);
    setUser(null);
    setRoles([]);
  }

  async function refresh() {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (token) await loadFromToken(token);
  }

  return (
    <Ctx.Provider value={{ loading, user, roles, signInWithToken, signOut, refresh }}>
      {children}
    </Ctx.Provider>
  );
}
