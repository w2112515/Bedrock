import { Drawer, Space, Descriptions, Typography } from 'antd'
import SignalMlLlmComparison from '@/components/SignalMlLlmComparison'
import SignalArbitrationDetail from '@/components/SignalArbitrationDetail'
import type { Signal } from '@/types/signal'

const { Title } = Typography

interface SignalDetailDrawerProps {
  signal: Signal | null
  open: boolean
  onClose: () => void
}

export default function SignalDetailDrawer({ signal, open, onClose }: SignalDetailDrawerProps) {
  if (!signal) return null

  return (
    <Drawer
      title={`信号详情 - ${signal.market}`}
      placement="right"
      width={720}
      onClose={onClose}
      open={open}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={5}>基础信息</Title>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="交易对">{signal.market}</Descriptions.Item>
            <Descriptions.Item label="信号类型">{signal.signal_type}</Descriptions.Item>
            <Descriptions.Item label="入场价">${signal.entry_price.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="止损价">${signal.stop_loss_price.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="目标价">${signal.profit_target_price.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="风险单位">{signal.risk_unit_r.toFixed(2)}R</Descriptions.Item>
            <Descriptions.Item label="建议仓位">
              {(signal.suggested_position_weight * 100).toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label="盈亏比">
              {signal.reward_risk_ratio ? `${signal.reward_risk_ratio.toFixed(2)}:1` : '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>

        <SignalMlLlmComparison signal={signal} />

        <SignalArbitrationDetail signal={signal} />
      </Space>
    </Drawer>
  )
}

