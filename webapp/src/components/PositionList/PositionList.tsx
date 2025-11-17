import { useState } from 'react'
import { Table, Button, Modal, Descriptions, Progress, Tag, message, Space } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Position, PositionEstimateResponse } from '@/types/position'
import { formatPrice, formatDate } from '@/utils/format'
import { portfolioService } from '@/services/portfolioService'
import CandlestickChart from '@/components/CandlestickChart'

interface PositionListProps {
  positions: Position[]
  loading?: boolean
}

export default function PositionList({ positions, loading }: PositionListProps) {
  const [estimateModalVisible, setEstimateModalVisible] = useState(false)
  const [estimateData, setEstimateData] = useState<PositionEstimateResponse | null>(null)
  const [estimateLoading, setEstimateLoading] = useState(false)
  const [chartModalVisible, setChartModalVisible] = useState(false)
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)

  const handleEstimate = async (position: Position) => {
    setEstimateLoading(true)
    try {
      const estimate = await portfolioService.estimatePosition({
        market: position.market,
        entry_price: position.entry_price,
        stop_loss_price: position.stop_loss_price,
        profit_target_price: position.profit_target_price,
        risk_unit_r: Math.abs(position.entry_price - position.stop_loss_price),
        suggested_position_weight: position.position_weight_used
      })
      setEstimateData(estimate)
      setEstimateModalVisible(true)
    } catch (error) {
      message.error('获取预估信息失败')
    } finally {
      setEstimateLoading(false)
    }
  }

  const columns: ColumnsType<Position> = [
    {
      title: '市场',
      dataIndex: 'market',
      key: 'market',
      width: 120
    },
    {
      title: '仓位大小',
      dataIndex: 'position_size',
      key: 'position_size',
      width: 120,
      render: (size: number | string) => Number(size).toFixed(4)
    },
    {
      title: '入场价',
      dataIndex: 'entry_price',
      key: 'entry_price',
      width: 120,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '当前价',
      dataIndex: 'current_price',
      key: 'current_price',
      width: 120,
      render: (price: number) => formatPrice(price)
    },
    {
      title: '未实现盈亏',
      dataIndex: 'unrealized_pnl',
      key: 'unrealized_pnl',
      width: 120,
      render: (pnl: number | null) => {
        if (pnl === null) return '-'
        const color = pnl >= 0 ? 'green' : 'red'
        return <span style={{ color }}>{formatPrice(pnl)}</span>
      }
    },
    {
      title: '实际仓位权重',
      dataIndex: 'position_weight_used',
      key: 'position_weight_used',
      width: 150,
      render: (weight: number) => (
        <Progress 
          percent={weight * 100} 
          size="small"
          strokeColor="#52c41a"
          format={(percent) => `${percent?.toFixed(1)}%`}
        />
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const color = status === 'OPEN' ? 'green' : 'default'
        return <Tag color={color}>{status}</Tag>
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
      width: 150,
      fixed: 'right',
      render: (_: any, record: Position) => (
        <Space size="small">
          <Button
            type="link"
            onClick={() => handleEstimate(record)}
            loading={estimateLoading}
          >
            预估
          </Button>
          <Button
            type="link"
            onClick={() => {
              setSelectedPosition(record)
              setChartModalVisible(true)
            }}
          >
            查看K线
          </Button>
        </Space>
      )
    }
  ]

  return (
    <>
      <Table
        columns={columns}
        dataSource={positions}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`
        }}
        scroll={{ x: 1300 }}
      />

      <Modal
        title={`${selectedPosition?.market} K线图`}
        open={chartModalVisible}
        onCancel={() => setChartModalVisible(false)}
        footer={null}
        width={900}
      >
        {selectedPosition && (
          <CandlestickChart
            symbol={selectedPosition.market}
            interval="1h"
            entryPrice={selectedPosition.entry_price}
            stopLossPrice={selectedPosition.stop_loss_price}
            profitTargetPrice={selectedPosition.profit_target_price}
            currentPrice={selectedPosition.current_price}
          />
        )}
      </Modal>

      <Modal
        title="仓位预估信息"
        open={estimateModalVisible}
        onCancel={() => setEstimateModalVisible(false)}
        footer={null}
        width={600}
      >
        {estimateData && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="市场">
              {estimateData.market}
            </Descriptions.Item>
            <Descriptions.Item label="预估仓位大小">
              {Number(estimateData.estimated_position_size).toFixed(4)}
            </Descriptions.Item>
            <Descriptions.Item label="预估成本">
              {formatPrice(Number(estimateData.estimated_cost))} USDT
            </Descriptions.Item>
            <Descriptions.Item label="实际仓位权重">
              <Progress
                percent={Number(estimateData.position_weight_used) * 100}
                size="small"
                format={(percent) => `${percent?.toFixed(2)}%`}
              />
            </Descriptions.Item>
            <Descriptions.Item label="手续费">
              {formatPrice(Number(estimateData.commission))} USDT
            </Descriptions.Item>
            <Descriptions.Item label="滑点成本">
              {formatPrice(Number(estimateData.slippage))} USDT
            </Descriptions.Item>
            <Descriptions.Item label="风险百分比">
              {Number(estimateData.risk_percentage).toFixed(2)}%
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  )
}

