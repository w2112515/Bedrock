import { Modal, Descriptions, Divider, Row, Col, Statistic, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useBacktest, useBacktestMetrics, useBacktestTrades } from '@/hooks/useBacktests'
import type { BacktestTrade, TradeType } from '@/types/backtest'
import { formatPrice, formatDate } from '@/utils/format'

interface BacktestResultProps {
  backtestId: string | null
  visible: boolean
  onClose: () => void
}

export default function BacktestResult({ backtestId, visible, onClose }: BacktestResultProps) {
  const { data: backtest } = useBacktest(backtestId || '')
  const { data: metrics } = useBacktestMetrics(backtestId || '')
  const { data: tradesData } = useBacktestTrades(backtestId || '', { limit: 10 })

  const tradeColumns: ColumnsType<BacktestTrade> = [
    {
      title: '类型',
      dataIndex: 'trade_type',
      key: 'trade_type',
      width: 80,
      render: (type: TradeType) => (
        <Tag color={type === 'ENTRY' ? 'green' : 'red'}>
          {type === 'ENTRY' ? '开仓' : '平仓'}
        </Tag>
      )
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      render: (qty: number) => qty.toFixed(4)
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '手续费',
      dataIndex: 'commission',
      key: 'commission',
      width: 80,
      render: (commission: number) => formatPrice(commission)
    },
    {
      title: '已实现盈亏',
      dataIndex: 'realized_pnl',
      key: 'realized_pnl',
      width: 100,
      render: (pnl: number | null) => {
        if (pnl === null) return '-'
        const color = pnl >= 0 ? 'green' : 'red'
        const prefix = pnl >= 0 ? '+' : ''
        return <span style={{ color }}>{prefix}{formatPrice(pnl)}</span>
      }
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 150,
      render: (date: string) => formatDate(date)
    }
  ]

  return (
    <Modal
      title="回测结果"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={1000}
    >
      {backtest && (
        <>
          <Descriptions title="任务详情" bordered column={2}>
            <Descriptions.Item label="策略">{backtest.strategy_name}</Descriptions.Item>
            <Descriptions.Item label="市场">{backtest.market}</Descriptions.Item>
            <Descriptions.Item label="时间间隔">{backtest.interval}</Descriptions.Item>
            <Descriptions.Item label="日期范围">
              {backtest.start_date} ~ {backtest.end_date}
            </Descriptions.Item>
            <Descriptions.Item label="初始余额">
              {backtest.initial_balance.toLocaleString()} USDT
            </Descriptions.Item>
            <Descriptions.Item label="最终余额">
              {backtest.final_balance?.toLocaleString()} USDT
            </Descriptions.Item>
          </Descriptions>

          <Divider />

          {metrics && (
            <>
              <h3>核心性能指标</h3>
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="投资回报率 (ROI)"
                    value={metrics.roi ? (metrics.roi * 100).toFixed(2) : 0}
                    suffix="%"
                    valueStyle={{ color: (metrics.roi || 0) >= 0 ? '#52c41a' : '#ff4d4f' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="胜率"
                    value={metrics.win_rate ? (metrics.win_rate * 100).toFixed(2) : 0}
                    suffix="%"
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="最大回撤"
                    value={metrics.max_drawdown ? (metrics.max_drawdown * 100).toFixed(2) : 0}
                    suffix="%"
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="夏普比率"
                    value={metrics.sharpe_ratio?.toFixed(2) || '-'}
                  />
                </Col>
              </Row>

              <Divider />

              <h3>交易统计</h3>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="总交易数" value={metrics.total_trades || 0} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="盈利交易"
                    value={metrics.winning_trades || 0}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="亏损交易"
                    value={metrics.losing_trades || 0}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
              </Row>

              <Divider />
            </>
          )}

          <h3>交易明细 (前10条)</h3>
          <Table
            columns={tradeColumns}
            dataSource={tradesData?.trades || []}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </>
      )}
    </Modal>
  )
}

