/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** FastAPI base URL; defaults to http://127.0.0.1:8000 (ADR-0011). */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
