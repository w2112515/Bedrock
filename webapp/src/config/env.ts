export const env = {
  dataHubBaseUrl: import.meta.env.VITE_DATAHUB_BASE_URL || '/api/datahub',
  decisionEngineBaseUrl: import.meta.env.VITE_DECISION_ENGINE_BASE_URL || '/api/decision',
  portfolioBaseUrl: import.meta.env.VITE_PORTFOLIO_BASE_URL || '/api/portfolio',
  backtestingBaseUrl: import.meta.env.VITE_BACKTESTING_BASE_URL || '/api/backtest',
  wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8006',
  
  appTitle: import.meta.env.VITE_APP_TITLE || 'Project Bedrock',
  appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
  appEnv: import.meta.env.VITE_APP_ENV || 'development',
  
  apiTimeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  
  debug: import.meta.env.VITE_DEBUG === 'true',
  
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD
} as const

export function validateEnv() {
  const required = [
    'VITE_DATAHUB_BASE_URL',
    'VITE_DECISION_ENGINE_BASE_URL',
    'VITE_PORTFOLIO_BASE_URL',
    'VITE_BACKTESTING_BASE_URL'
  ]
  
  const missing = required.filter(key => !import.meta.env[key])
  
  if (missing.length > 0) {
    console.warn(`Missing environment variables: ${missing.join(', ')}`)
  }
}

