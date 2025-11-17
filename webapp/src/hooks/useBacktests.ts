import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { backtestService } from '@/services/backtestService'
import type { CreateBacktestRequest } from '@/types/backtest'

/**
 * 获取回测任务列表
 * 条件轮询: 仅当存在RUNNING或PENDING任务时每10秒刷新
 */
export function useBacktests(params?: {
  limit?: number
  offset?: number
  status?: string
  market?: string
}) {
  const { data, ...rest } = useQuery({
    queryKey: ['backtests', params],
    queryFn: () => backtestService.getBacktests(params),
    staleTime: 5 * 1000,  // 5秒 - 回测任务状态变化较快
    refetchInterval: (data) => {
      // 条件轮询: 仅当存在RUNNING或PENDING任务时启用
      const hasRunningTasks = data?.backtests?.some(
        b => b.status === 'RUNNING' || b.status === 'PENDING'
      )
      return hasRunningTasks ? 10 * 1000 : false  // 10秒轮询
    }
  })

  return { data, ...rest }
}

/**
 * 获取单个回测任务详情
 */
export function useBacktest(backtestId: string) {
  return useQuery({
    queryKey: ['backtest', backtestId],
    queryFn: () => backtestService.getBacktestById(backtestId),
    enabled: !!backtestId,
    staleTime: 5 * 1000
  })
}

/**
 * 获取回测性能指标
 */
export function useBacktestMetrics(backtestId: string) {
  return useQuery({
    queryKey: ['backtest-metrics', backtestId],
    queryFn: () => backtestService.getBacktestMetrics(backtestId),
    enabled: !!backtestId,
    staleTime: 60 * 1000  // 1分钟 - 指标数据不会变化
  })
}

/**
 * 获取回测交易明细
 */
export function useBacktestTrades(
  backtestId: string,
  params?: {
    limit?: number
    offset?: number
  }
) {
  return useQuery({
    queryKey: ['backtest-trades', backtestId, params],
    queryFn: () => backtestService.getBacktestTrades(backtestId, params),
    enabled: !!backtestId,
    staleTime: 60 * 1000  // 1分钟 - 交易明细不会变化
  })
}

/**
 * 创建回测任务 (Mutation)
 */
export function useCreateBacktest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateBacktestRequest) => backtestService.createBacktest(data),
    onSuccess: () => {
      // 创建成功后刷新任务列表
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    }
  })
}

