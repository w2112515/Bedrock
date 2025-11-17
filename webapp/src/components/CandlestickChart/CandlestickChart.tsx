import { useEffect, useRef, useState } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData } from 'lightweight-charts'
import { Select, Spin, Alert } from 'antd'
import { useKlines } from '@/hooks/useKlines'

interface CandlestickChartProps {
  symbol: string
  interval?: string
  entryPrice?: number | string
  stopLossPrice?: number | string
  profitTargetPrice?: number | string
  currentPrice?: number | string
}

export default function CandlestickChart({ 
  symbol, 
  interval: initialInterval = '1h',
  entryPrice,
  stopLossPrice,
  profitTargetPrice,
  currentPrice
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [interval, setInterval] = useState(initialInterval)
  
  // 将BTC/USDT转换为BTCUSDT
  const symbolFormatted = symbol.replace('/', '')
  
  const { data, isLoading, error } = useKlines({
    symbol: symbolFormatted,
    interval,
    limit: 100
  })

  useEffect(() => {
    if (!chartContainerRef.current) return

    // 创建图表
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333'
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' }
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false
      }
    })

    // 添加K线系列
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350'
    })

    chartRef.current = chart
    seriesRef.current = candlestickSeries

    // 响应式调整
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!data || !seriesRef.current) return

    try {
      console.log('=== K线图数据加载 ===')
      console.log('当前时间周期:', interval)
      console.log('原始数据条数:', data.length)

      // 设置K线数据
      const candlestickData: CandlestickData[] = (data || [])
        .filter(k => {
          // 过滤无效数据
          return k.open_time &&
                 k.open_price != null &&
                 k.high_price != null &&
                 k.low_price != null &&
                 k.close_price != null
        })
        .sort((a, b) => a.open_time - b.open_time) // 按时间升序排序（lightweight-charts要求）
        .map(k => ({
          time: Math.floor(k.open_time / 1000) as any, // 转换为秒并确保是整数
          open: Number(k.open_price),
          high: Number(k.high_price),
          low: Number(k.low_price),
          close: Number(k.close_price)
        }))

      console.log('过滤后K线数据条数:', candlestickData.length)
      console.log('K线数据 (前3条):', candlestickData.slice(0, 3))
      console.log('K线数据 (后3条):', candlestickData.slice(-3))

      // 设置K线数据
      seriesRef.current.setData(candlestickData)

      // 输出价格线信息（用于诊断）
      console.log('=== 价格线信息 ===')
      if (entryPrice) {
        console.log('入场价:', Number(entryPrice))
      }
      if (stopLossPrice) {
        console.log('止损价:', Number(stopLossPrice))
      }
      if (profitTargetPrice) {
        console.log('目标价:', Number(profitTargetPrice))
      }
      if (currentPrice) {
        console.log('当前价:', Number(currentPrice))
      }

      // 添加价格线（确保转换为数字类型）
      if (entryPrice) {
        seriesRef.current.createPriceLine({
          price: Number(entryPrice),
          color: '#1890ff',
          lineWidth: 2,
          lineStyle: 2, // 虚线
          axisLabelVisible: true,
          title: '入场价'
        })
      }

      if (stopLossPrice) {
        seriesRef.current.createPriceLine({
          price: Number(stopLossPrice),
          color: '#ff4d4f',
          lineWidth: 2,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '止损价'
        })
      }

      if (profitTargetPrice) {
        seriesRef.current.createPriceLine({
          price: Number(profitTargetPrice),
          color: '#52c41a',
          lineWidth: 2,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '目标价'
        })
      }

      if (currentPrice) {
        seriesRef.current.createPriceLine({
          price: Number(currentPrice),
          color: '#faad14',
          lineWidth: 2,
          lineStyle: 0, // 实线
          axisLabelVisible: true,
          title: '当前价'
        })
      }

      // 自动缩放时间轴
      if (chartRef.current && candlestickData.length > 0) {
        chartRef.current.timeScale().fitContent()
      }

      console.log('=== K线图数据加载完成 ===')
    } catch (err) {
      console.error('❌ K线图数据加载错误:', err)
    }
  }, [data, entryPrice, stopLossPrice, profitTargetPrice, currentPrice, interval])

  if (error) {
    return (
      <Alert
        message="加载K线数据失败"
        description="无法获取K线数据，请稍后重试"
        type="error"
        showIcon
      />
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ marginRight: 8 }}>时间周期：</span>
          <Select
            value={interval}
            onChange={setInterval}
            style={{ width: 120 }}
            options={[
              { label: '1小时', value: '1h' },
              { label: '4小时', value: '4h' },
              { label: '1天', value: '1d' }
            ]}
          />
        </div>
        <div style={{ fontSize: 12, color: '#999' }}>
          {data && `显示最近 ${data.length} 根K线`}
        </div>
      </div>
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 100 }}>
          <Spin size="large" tip="加载K线数据中..." />
        </div>
      ) : (
        <div ref={chartContainerRef} style={{ position: 'relative' }} />
      )}
    </div>
  )
}

