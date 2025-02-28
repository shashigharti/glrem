import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set) => ({
      id: 1,
      userid: "aliraza",
      username: null,
      isAuthenticated: false,
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
