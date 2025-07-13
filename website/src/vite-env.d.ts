/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WEBHOOK_ID: string
  readonly VITE_N8N_URL: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_DEBUG: string
  // Add more env variables as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}