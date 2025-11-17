// ==================== 枚举类型 ====================

/**
 * 回测任务状态
 */
export type BacktestStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

/**
 * 策略名称
 */
export type StrategyName = 'Rules Only' | 'Rules + ML'

/**
 * K线时间间隔
 */
export type Interval = '1h' | '4h' | '1d'

/**
 * 交易类型
 */
export type TradeType = 'ENTRY' | 'EXIT'

// ==================== 请求模型 ====================

/**
 * 创建回测任务请求
 */
export interface CreateBacktestRequest {
  strategy_name: StrategyName
  market: string
  interval: Interval
  start_date: string          // ISO date format: "2024-01-01"
  end_date: string            // ISO date format: "2024-12-31"
  initial_balance: number     // 默认: 100000
}

// ==================== 响应模型 ====================

/**
 * 回测任务响应
 */
export interface BacktestRun {
  id: string
  strategy_name: string
  market: string
  interval: string
  start_date: string
  end_date: string
  initial_balance: number
  final_balance: number | null
  status: BacktestStatus
  progress: number              // 0.0 - 1.0
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

/**
 * 回测列表响应
 */
export interface BacktestListResponse {
  backtests: BacktestRun[]
  total: number
  page: number
  page_size: number
}

/**
 * 回测性能指标响应
 */
export interface BacktestMetrics {
  id: string
  backtest_run_id: string
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number              // 0.0 - 1.0
  avg_win: number
  avg_loss: number
  profit_factor: number
  max_drawdown: number          // 0.0 - 1.0
  sharpe_ratio: number | null
  calmar_ratio: number | null
  sortino_ratio: number | null
  omega_ratio: number | null
  total_commission: number
  total_slippage: number
  roi: number                   // 0.0 - 1.0
  created_at: string
}

/**
 * 回测交易响应
 */
export interface BacktestTrade {
  id: string
  backtest_run_id: string
  market: string
  signal_id: string | null
  trade_type: TradeType
  quantity: number
  price: number
  timestamp: string
  commission: number
  slippage: number
  realized_pnl: number | null
  created_at: string
}

/**
 * 回测交易列表响应
 */
export interface BacktestTradeListResponse {
  trades: BacktestTrade[]
  total: number
  page: number
  page_size: number
}

// ==================== 常量定义 ====================

/**
 * 策略选项
 */
export const STRATEGY_OPTIONS = [
  { label: '仅规则引擎', value: 'Rules Only' as StrategyName },
  { label: '规则引擎 + 机器学习', value: 'Rules + ML' as StrategyName }
] as const

/**
 * 市场选项 (预设热门交易对)
 */
export const MARKET_OPTIONS = [
  { label: 'BTC/USDT', value: 'BTC/USDT' },
  { label: 'ETH/USDT', value: 'ETH/USDT' },
  { label: 'BNB/USDT', value: 'BNB/USDT' },
  { label: 'SOL/USDT', value: 'SOL/USDT' }
] as const

/**
 * 时间间隔选项
 */
export const INTERVAL_OPTIONS = [
  { label: '1小时', value: '1h' as Interval },
  { label: '4小时', value: '4h' as Interval },
  { label: '1天', value: '1d' as Interval }
] as const

/**
 * 状态标签颜色映射
 */
export const STATUS_COLOR_MAP: Record<BacktestStatus, string> = {
  PENDING: 'default',
  RUNNING: 'processing',
  COMPLETED: 'success',
  FAILED: 'error'
} as const

/**
 * 状态标签文本映射
 */
export const STATUS_TEXT_MAP: Record<BacktestStatus, string> = {
  PENDING: '等待中',
  RUNNING: '运行中',
  COMPLETED: '已完成',
  FAILED: '失败'
} as const

