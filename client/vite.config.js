import react from "@vitejs/plugin-react";
import path from "path";

export default {
  plugins: [react()],

  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/assets/styles/custom" as *;`,
        quietDeps: true,
      },
    },
  },

  optimizeDeps: {
    include: ["@aws-sdk/client-s3"],
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@assets": path.resolve(__dirname, "src/assets"),
    },
  },
};
