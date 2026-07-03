import { create } from "zustand";
import { authApi } from "../api/endpoints";
import { loadStoredRefresh, setOnAuthLost, setTokens } from "../api/client";
import type { Me } from "../types/api";

interface AuthState {
  user: Me | null;
  status: "loading" | "authed" | "anon";
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  bootstrap: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  status: "loading",

  login: async (email, password) => {
    const tokens = await authApi.login(email, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await authApi.me();
    set({ user: me, status: "authed" });
  },

  logout: () => {
    setTokens(null, null);
    set({ user: null, status: "anon" });
  },

  bootstrap: async () => {
    // Re-establish a session from a stored refresh token on reload.
    const refresh = loadStoredRefresh();
    if (!refresh) {
      set({ status: "anon" });
      return;
    }
    try {
      setTokens(null, refresh);
      const me = await authApi.me(); // triggers a refresh inside the client
      set({ user: me, status: "authed" });
    } catch {
      setTokens(null, null);
      set({ status: "anon" });
    }
  },
}));

// Wire the client's "auth lost" callback to the store once.
setOnAuthLost(() => {
  setTokens(null, null);
  useAuth.setState({ user: null, status: "anon" });
});
