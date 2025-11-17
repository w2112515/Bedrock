import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Trade } from '@/types/trade'
import { formatPrice, formatDate } from '@/utils/format'

interface TradeListProps {
  trades: Trade[]
  loading?: boolean
}

export default function TradeList({ trades, loading }: TradeListProps) {
  const columns: ColumnsType<Trade> = [
    {
      title: '交易类型',
      dataIndex: 'trade_type',
      key: 'trade_type',
      width: 100,
      render: (type: string) => {
        const color = type === 'ENTRY' ? 'green' : 'red'
        const text = type === 'ENTRY' ? '开仓' : '平仓'
        return <Tag color={color}>{text}</Tag>
      }
    },
    {
      title: '市场',
      dataIndex: 'market',
      key: 'market',
      width: 120
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 120,
      render: (quantity: number | string) => Number(quantity).toFixed(4)
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 120,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '手续费',
      dataIndex: 'commission',
      key: 'commission',
      width: 100,
      render: (commission: number) => formatPrice(commission)
    },
    {
      title: '已实现盈亏',
      dataIndex: 'realized_pnl',
      key: 'realized_pnl',
      width: 120,
      render: (pnl: number | null) => {
        if (pnl === null) return '-'
        const color = pnl >= 0 ? 'green' : 'red'
        const prefix = pnl >= 0 ? '+' : ''
        return <span style={{ color }}>{prefix}{formatPrice(pnl)}</span>
      }
    },
    {
      title: '成交时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (date: string) => formatDate(date)
    }
  ]

  return (
    <Table
      columns={columns}
      dataSource={trades}
      rowKey="id"
      loading={loading}
      pagination={{
        pageSize: 20,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`
      }}
      scroll={{ x: 1000 }}
    />
  )
}

