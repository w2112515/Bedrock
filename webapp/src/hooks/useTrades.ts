import { useQuery } from '@tanstack/react-query'
import { tradeService } from '@/services/tradeService'

export function useTrades(params?: {
  position_id?: string
  trade_type?: 'ENTRY' | 'EXIT'
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['trades', params],
    queryFn: () => tradeService.getTrades(params),
    staleTime: 5 * 60 * 1000, // 5分钟
    refetchInterval: 30 * 1000 // 30秒自动刷新
  })
}

export function useTradeById(tradeId: string) {
  return useQuery({
    queryKey: ['trade', tradeId],
    queryFn: () => tradeService.getTradeById(tradeId),
    enabled: !!tradeId
  })
}

