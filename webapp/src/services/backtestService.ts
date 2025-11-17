import { backtestingApi } from './api'
import type {
  CreateBacktestRequest,
  BacktestRun,
  BacktestListResponse,
  BacktestMetrics,
  BacktestTradeListResponse
} from '@/types/backtest'

class BacktestService {
  /**
   * 创建回测任务
   * POST /v1/backtests
   */
  async createBacktest(data: CreateBacktestRequest): Promise<BacktestRun> {
    const response = await backtestingApi.post<BacktestRun>('/v1/backtests', data)
    return response.data
  }

  /**
   * 获取回测任务列表 (带分页转换)
   * GET /v1/backtests?page={page}&page_size={page_size}&status={status}&market={market}
   */
  async getBacktests(params?: {
    limit?: number
    offset?: number
    status?: string
    market?: string
  }): Promise<BacktestListResponse> {
    // 转换分页参数: limit/offset -> page/page_size
    const page = params?.offset 
      ? Math.floor(params.offset / (params.limit || 20)) + 1 
      : 1
    const page_size = params?.limit || 20

    const response = await backtestingApi.get<BacktestListResponse>('/v1/backtests', {
      params: {
        page,
        page_size,
        status: params?.status,
        market: params?.market
      }
    })
    return response.data
  }

  /**
   * 获取单个回测任务详情
   * GET /v1/backtests/{backtest_id}
   */
  async getBacktestById(backtestId: string): Promise<BacktestRun> {
    const response = await backtestingApi.get<BacktestRun>(`/v1/backtests/${backtestId}`)
    return response.data
  }

  /**
   * 获取回测性能指标
   * GET /v1/backtests/{backtest_id}/metrics
   */
  async getBacktestMetrics(backtestId: string): Promise<BacktestMetrics> {
    const response = await backtestingApi.get<BacktestMetrics>(
      `/v1/backtests/${backtestId}/metrics`
    )
    return response.data
  }

  /**
   * 获取回测交易明细
   * GET /v1/backtests/{backtest_id}/trades?page={page}&page_size={page_size}
   */
  async getBacktestTrades(
    backtestId: string,
    params?: {
      limit?: number
      offset?: number
    }
  ): Promise<BacktestTradeListResponse> {
    // 转换分页参数
    const page = params?.offset 
      ? Math.floor(params.offset / (params.limit || 20)) + 1 
      : 1
    const page_size = params?.limit || 20

    const response = await backtestingApi.get<BacktestTradeListResponse>(
      `/v1/backtests/${backtestId}/trades`,
      {
        params: { page, page_size }
      }
    )
    return response.data
  }
}

export const backtestService = new BacktestService()
export default backtestService

