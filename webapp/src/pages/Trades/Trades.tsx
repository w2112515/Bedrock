import { useState } from 'react'
import { Card, Row, Col, Select, Button, Space, Statistic } from 'antd'
import TradeList from '@/components/TradeList'
import { useTrades } from '@/hooks/useTrades'

export default function Trades() {
  const [tradeType, setTradeType] = useState<'ENTRY' | 'EXIT' | undefined>(undefined)
  const { data: tradesData, isLoading } = useTrades({ 
    trade_type: tradeType,
    limit: 100 
  })

  const handleReset = () => {
    setTradeType(undefined)
  }

  return (
    <div style={{ padding: '24px' }}>
      <h1>交易历史</h1>
      
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总交易数"
              value={tradesData?.total || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="开仓交易"
              value={tradesData?.trades.filter(t => t.trade_type === 'ENTRY').length || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平仓交易"
              value={tradesData?.trades.filter(t => t.trade_type === 'EXIT').length || 0}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总已实现盈亏"
              value={tradesData?.trades
                .filter(t => t.realized_pnl !== null)
                .reduce((sum, t) => sum + (t.realized_pnl || 0), 0)
                .toFixed(2) || 0}
              valueStyle={{ 
                color: (tradesData?.trades
                  .filter(t => t.realized_pnl !== null)
                  .reduce((sum, t) => sum + (t.realized_pnl || 0), 0) || 0) >= 0 
                  ? '#52c41a' 
                  : '#ff4d4f' 
              }}
              prefix="$"
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: '24px' }}>
        <Space size="middle">
          <span>筛选条件：</span>
          <Select
            placeholder="交易类型"
            value={tradeType}
            onChange={setTradeType}
            style={{ width: 150 }}
            allowClear
            options={[
              { label: '开仓', value: 'ENTRY' },
              { label: '平仓', value: 'EXIT' }
            ]}
          />
          <Button onClick={handleReset}>重置</Button>
        </Space>
      </Card>

      <Card>
        <TradeList 
          trades={tradesData?.trades || []} 
          loading={isLoading}
        />
      </Card>
    </div>
  )
}

