import { Card, Row, Col, Statistic, Divider } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import SignalList from '@/components/SignalList'
import PositionList from '@/components/PositionList'
import ArbitrationStatsCard from '@/components/ArbitrationStatsCard'
import { useSignals } from '@/hooks/useSignals'
import { usePositions, useAccount, useStats } from '@/hooks/usePositions'

export default function Dashboard() {
  const { data: signalsData, isLoading: signalsLoading } = useSignals({ limit: 10 })
  const { data: positionsData, isLoading: positionsLoading } = usePositions({ limit: 10 })
  const { data: account } = useAccount()
  const { data: stats } = useStats()

  return (
    <div style={{ padding: '24px' }}>
      <h1>仪表盘</h1>
      
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="账户余额"
              value={account?.balance || 0}
              precision={2}
              valueStyle={{ color: '#3f8600' }}
              prefix="$"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未实现盈亏"
              value={stats?.total_pnl || 0}
              precision={2}
              valueStyle={{ color: (stats?.total_pnl || 0) >= 0 ? '#3f8600' : '#cf1322' }}
              prefix={(stats?.total_pnl || 0) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              suffix="USDT"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="胜率"
              value={stats?.win_rate || 0}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="持仓数量"
              value={stats?.open_positions || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={24}>
          <ArbitrationStatsCard days={7} />
        </Col>
      </Row>

      <Divider orientation="left">最新信号</Divider>
      <SignalList
        signals={signalsData?.signals || []}
        loading={signalsLoading}
      />

      <Divider orientation="left">当前仓位</Divider>
      <PositionList 
        positions={positionsData?.positions || []} 
        loading={positionsLoading}
      />
    </div>
  )
}

