import { useState } from 'react'
import { Table, Tag, Progress, Tooltip, Space, Button, Modal } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Signal, OnchainSignalsData } from '@/types/signal'
import { formatPrice, formatWeight, formatDate } from '@/utils/format'
import { ONCHAIN_SIGNAL_CONFIG } from '@/config/constants'
import CandlestickChart from '@/components/CandlestickChart'
import SignalDetail from '@/components/SignalDetail/SignalDetail'
import SignalDetailDrawer from '@/components/SignalDetailDrawer'

interface SignalListProps {
  signals: Signal[]
  loading?: boolean
}

function OnchainSignals({ data }: { data: OnchainSignalsData | null }) {
  if (!data || Object.keys(data).length === 0) {
    return <span style={{ color: '#999' }}>无链上数据</span>
  }

  return (
    <Space size="small" wrap>
      {Object.entries(data).map(([key, value]) => {
        const config = ONCHAIN_SIGNAL_CONFIG[key as keyof typeof ONCHAIN_SIGNAL_CONFIG]
        if (!config || !value) return null

        return (
          <Tooltip 
            key={key}
            title={
              <div>
                <div>大额转账次数: {data.large_transfer_count || '-'}</div>
                <div>交易所净流出量: {data.exchange_netflow || '-'}</div>
                <div>聪明钱净买入量: {data.smart_money_netbuy || '-'}</div>
                <div>活跃地址增长率: {data.active_address_growth || '-'}</div>
              </div>
            }
          >
            <Tag color={config.color}>{config.label}</Tag>
          </Tooltip>
        )
      })}
    </Space>
  )
}

export default function SignalList({ signals, loading }: SignalListProps) {
  const [chartModalVisible, setChartModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)

  const columns: ColumnsType<Signal> = [
    {
      title: '市场',
      dataIndex: 'market',
      key: 'market',
      width: 120
    },
    {
      title: '信号类型',
      dataIndex: 'signal_type',
      key: 'signal_type',
      width: 120,
      render: (type: string) => {
        const color = type === 'PULLBACK_BUY' ? 'blue' : type === 'OOPS_BUY' ? 'orange' : 'red'
        return <Tag color={color}>{type}</Tag>
      }
    },
    {
      title: '入场价',
      dataIndex: 'entry_price',
      key: 'entry_price',
      width: 120,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '止损价',
      dataIndex: 'stop_loss_price',
      key: 'stop_loss_price',
      width: 120,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '目标价',
      dataIndex: 'profit_target_price',
      key: 'profit_target_price',
      width: 120,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '盈亏比',
      dataIndex: 'reward_risk_ratio',
      key: 'reward_risk_ratio',
      width: 100,
      render: (ratio: number | string | null) => {
        if (!ratio) return '-'
        const numRatio = Number(ratio)
        const color = numRatio > 2 ? 'green' : numRatio >= 1 ? 'yellow' : 'red'
        return <Tag color={color}>{numRatio.toFixed(2)}:1</Tag>
      }
    },
    {
      title: '建议仓位权重',
      dataIndex: 'suggested_position_weight',
      key: 'suggested_position_weight',
      width: 150,
      render: (weight: number) => (
        <Tooltip title={formatWeight(weight)}>
          <Progress 
            percent={weight * 100} 
            size="small"
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            format={(percent) => `${percent?.toFixed(1)}%`}
          />
        </Tooltip>
      ),
      sorter: (a: Signal, b: Signal) => a.suggested_position_weight - b.suggested_position_weight
    },
    {
      title: '规则评分',
      dataIndex: 'rule_engine_score',
      key: 'rule_engine_score',
      width: 100,
      render: (score: number | string) => Number(score).toFixed(1)
    },
    {
      title: 'ML置信度',
      dataIndex: 'ml_confidence_score',
      key: 'ml_confidence_score',
      width: 150,
      render: (score: number | null) => {
        if (score === null || score === undefined) {
          return <span style={{ color: '#999' }}>-</span>
        }

        const percent = score * 100
        let strokeColor: string

        if (score >= 0.8) {
          strokeColor = '#52c41a' // 绿色
        } else if (score >= 0.6) {
          strokeColor = '#1890ff' // 蓝色
        } else {
          strokeColor = '#faad14' // 橙色
        }

        return (
          <Tooltip title={`置信度: ${score.toFixed(4)}`}>
            <Progress
              percent={percent}
              size="small"
              strokeColor={strokeColor}
              format={(percent) => `${percent?.toFixed(1)}%`}
            />
          </Tooltip>
        )
      },
      sorter: (a: Signal, b: Signal) => {
        const scoreA = a.ml_confidence_score ?? -1
        const scoreB = b.ml_confidence_score ?? -1
        return scoreA - scoreB
      }
    },
    {
      title: 'LLM情绪',
      dataIndex: 'llm_sentiment',
      key: 'llm_sentiment',
      width: 100,
      render: (sentiment: string | null) => {
        if (!sentiment) {
          return <span style={{ color: '#999' }}>-</span>
        }

        const sentimentUpper = sentiment.toUpperCase()
        let color: string
        let text: string

        switch (sentimentUpper) {
          case 'BULLISH':
            color = 'green'
            text = '看涨'
            break
          case 'BEARISH':
            color = 'red'
            text = '看跌'
            break
          case 'NEUTRAL':
            color = 'default'
            text = '中性'
            break
          default:
            color = 'default'
            text = sentiment
        }

        return <Tag color={color}>{text}</Tag>
      },
      filters: [
        { text: '看涨', value: 'BULLISH' },
        { text: '看跌', value: 'BEARISH' },
        { text: '中性', value: 'NEUTRAL' }
      ],
      onFilter: (value: any, record: Signal) => {
        if (!record.llm_sentiment) return false
        return record.llm_sentiment.toUpperCase() === value
      }
    },
    {
      title: '仲裁结果',
      dataIndex: 'final_decision',
      key: 'final_decision',
      width: 100,
      render: (decision: string | null) => {
        if (!decision) {
          return <Tag>待定</Tag>
        }
        return (
          <Tag color={decision === 'APPROVED' ? 'success' : 'error'}>
            {decision === 'APPROVED' ? '通过' : '拒绝'}
          </Tag>
        )
      },
      filters: [
        { text: '通过', value: 'APPROVED' },
        { text: '拒绝', value: 'REJECTED' }
      ],
      onFilter: (value: any, record: Signal) => record.final_decision === value
    },
    {
      title: '链上指标',
      dataIndex: 'onchain_signals',
      key: 'onchain_signals',
      width: 200,
      render: (data: OnchainSignalsData | null) => <OnchainSignals data={data} />
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
      width: 250,
      fixed: 'right',
      render: (_: any, record: Signal) => (
        <Space size="small">
          <Button
            type="link"
            onClick={() => {
              setSelectedSignal(record)
              setChartModalVisible(true)
            }}
          >
            查看K线
          </Button>
          <Button
            type="link"
            onClick={() => {
              setSelectedSignal(record)
              setDetailModalVisible(true)
            }}
          >
            查看详情
          </Button>
          <Button
            type="link"
            onClick={() => {
              setSelectedSignal(record)
              setDrawerVisible(true)
            }}
          >
            仲裁详情
          </Button>
        </Space>
      )
    }
  ]

  return (
    <>
      <Table
        columns={columns}
        dataSource={signals}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`
        }}
        scroll={{ x: 1800 }}
      />

      <Modal
        title={`${selectedSignal?.market} K线图`}
        open={chartModalVisible}
        onCancel={() => setChartModalVisible(false)}
        footer={null}
        width={900}
      >
        {selectedSignal && (
          <CandlestickChart
            symbol={selectedSignal.market}
            interval="1h"
            entryPrice={selectedSignal.entry_price}
            stopLossPrice={selectedSignal.stop_loss_price}
            profitTargetPrice={selectedSignal.profit_target_price}
          />
        )}
      </Modal>

      <SignalDetail
        signal={selectedSignal}
        visible={detailModalVisible}
        onClose={() => setDetailModalVisible(false)}
      />

      <SignalDetailDrawer
        signal={selectedSignal}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
      />
    </>
  )
}

