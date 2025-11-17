import { Card } from 'antd'
import SignalList from '@/components/SignalList'
import { useSignals } from '@/hooks/useSignals'

export default function Signals() {
  const { data, isLoading } = useSignals()

  return (
    <div style={{ padding: '24px' }}>
      <h1>交易信号</h1>
      <Card>
        <SignalList
          signals={data?.signals || []}
          loading={isLoading}
        />
      </Card>
    </div>
  )
}

