import BacktestConfig from '@/components/BacktestConfig'
import BacktestTaskList from '@/components/BacktestTaskList'

export default function Backtest() {
  return (
    <div style={{ padding: '24px' }}>
      <h1>回测管理</h1>
      
      <BacktestConfig />
      
      <BacktestTaskList />
    </div>
  )
}

