/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DATAHUB_BASE_URL: string
  readonly VITE_DECISION_ENGINE_BASE_URL: string
  readonly VITE_PORTFOLIO_BASE_URL: string
  readonly VITE_BACKTESTING_BASE_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
  readonly VITE_APP_ENV: string
  readonly VITE_API_TIMEOUT: string
  readonly VITE_DEBUG: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

