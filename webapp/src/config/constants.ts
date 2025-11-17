export const API_TIMEOUT = 30000

export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

export const SIGNAL_TYPES = {
  PULLBACK_BUY: 'PULLBACK_BUY',
  OOPS_BUY: 'OOPS_BUY',
  OOPS_SELL: 'OOPS_SELL'
} as const

export const POSITION_STATUS = {
  OPEN: 'OPEN',
  CLOSED: 'CLOSED'
} as const

export const BACKTEST_STATUS = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED'
} as const

export const ONCHAIN_SIGNAL_CONFIG = {
  whale_active: { label: '鲸鱼活跃', color: 'blue' },
  fund_outflow: { label: '资金流出', color: 'green' },
  smart_money_buy: { label: '聪明钱买入', color: 'gold' },
  address_active_increase: { label: '地址活跃度上升', color: 'purple' }
} as const

