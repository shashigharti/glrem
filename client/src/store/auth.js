import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set) => ({
      isAuthenticated: false,
      userid: 1,
      username: null,
      login: (username) => set({ isAuthenticated: true, username }),
      logout: () => set({ isAuthenticated: false, username: null }),
    }),
    {
      name: "auth-storage",
      getStorage: () => localStorage,
    },
  ),
);

export default useAuthStore;
