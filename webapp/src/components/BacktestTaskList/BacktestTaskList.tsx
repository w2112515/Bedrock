import { useState } from 'react'
import { Card, Table, Tag, Progress, Button } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useBacktests } from '@/hooks/useBacktests'
import BacktestResult from '@/components/BacktestResult'
import type { BacktestRun, BacktestStatus } from '@/types/backtest'
import { STATUS_COLOR_MAP, STATUS_TEXT_MAP } from '@/types/backtest'
import { formatDate } from '@/utils/format'

export default function BacktestTaskList() {
  const { data, isLoading } = useBacktests()
  const [selectedBacktestId, setSelectedBacktestId] = useState<string | null>(null)
  const [resultModalVisible, setResultModalVisible] = useState(false)

  const handleViewResult = (backtestId: string) => {
    setSelectedBacktestId(backtestId)
    setResultModalVisible(true)
  }

  const columns: ColumnsType<BacktestRun> = [
    {
      title: '策略',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      width: 150
    },
    {
      title: '市场',
      dataIndex: 'market',
      key: 'market',
      width: 120
    },
    {
      title: '时间间隔',
      dataIndex: 'interval',
      key: 'interval',
      width: 100
    },
    {
      title: '日期范围',
      key: 'date_range',
      width: 200,
      render: (_, record) => `${record.start_date} ~ ${record.end_date}`
    },
    {
      title: '初始余额',
      dataIndex: 'initial_balance',
      key: 'initial_balance',
      width: 120,
      render: (balance: number) => `${balance.toLocaleString()} USDT`
    },
    {
      title: '最终余额',
      dataIndex: 'final_balance',
      key: 'final_balance',
      width: 120,
      render: (balance: number | null) => 
        balance !== null ? `${balance.toLocaleString()} USDT` : '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: BacktestStatus) => (
        <Tag color={STATUS_COLOR_MAP[status]}>
          {STATUS_TEXT_MAP[status]}
        </Tag>
      )
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number, record: BacktestRun) => {
        if (record.status === 'RUNNING') {
          return <Progress percent={Math.round(progress * 100)} size="small" />
        }
        return '-'
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDate(date)
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record: BacktestRun) => (
        <Button
          type="link"
          disabled={record.status !== 'COMPLETED'}
          onClick={() => handleViewResult(record.id)}
        >
          查看结果
        </Button>
      )
    }
  ]

  return (
    <>
      <Card title="回测任务列表">
        <Table
          columns={columns}
          dataSource={data?.backtests || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            total: data?.total || 0,
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      <BacktestResult
        backtestId={selectedBacktestId}
        visible={resultModalVisible}
        onClose={() => setResultModalVisible(false)}
      />
    </>
  )
}

