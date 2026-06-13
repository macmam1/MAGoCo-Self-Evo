import { create } from "zustand";
import { persist } from "zustand/middleware";
import authApi, { type LoginPayload, type RegisterPayload, type User } from "@/api/auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      async login(payload) {
        set({ isLoading: true, error: null });
        try {
          const tokens = await authApi.login(payload);
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          // Fetch user profile
          await get().fetchMe();
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : "Login failed";
          set({ isLoading: false, error: message });
          throw err;
        }
      },

      async register(payload) {
        set({ isLoading: true, error: null });
        try {
          await authApi.register(payload);
          // Auto-login after register
          await get().login({
            username_or_email: payload.username,
            password: payload.password,
          });
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : "Registration failed";
          set({ isLoading: false, error: message });
          throw err;
        }
      },

      async logout() {
        try {
          await authApi.logout();
        } catch {
          // Ignore — even if API fails, clear local state
        }
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      async fetchMe() {
        try {
          const user = await authApi.me();
          set({ user });
        } catch {
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
        }
      },

      clearError() {
        set({ error: null });
      },
    }),
    {
      name: "magoco-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
);
