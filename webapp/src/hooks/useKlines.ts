import { useQuery } from '@tanstack/react-query'
import { klineService } from '@/services/klineService'

export function useKlines(params: {
  symbol: string
  interval: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['klines', params],
    queryFn: () => klineService.getKlines(params),
    staleTime: 5 * 60 * 1000, // 5分钟 - K线数据变化不频繁
    cacheTime: 10 * 60 * 1000, // 10分钟 - 保留缓存更长时间
    enabled: !!params.symbol && !!params.interval
  })
}

