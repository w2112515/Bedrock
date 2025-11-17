import { Card } from 'antd'
import PositionList from '@/components/PositionList'
import { usePositions } from '@/hooks/usePositions'

export default function Positions() {
  const { data, isLoading } = usePositions()

  return (
    <div style={{ padding: '24px' }}>
      <h1>持仓管理</h1>
      <Card>
        <PositionList 
          positions={data?.positions || []} 
          loading={isLoading}
        />
      </Card>
    </div>
  )
}

