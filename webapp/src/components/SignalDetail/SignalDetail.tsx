import { Modal, Descriptions, Tag, Progress, Tooltip, Space } from 'antd'
import type { Signal, OnchainSignalsData } from '@/types/signal'
import { formatPrice, formatWeight, formatDate } from '@/utils/format'
import { ONCHAIN_SIGNAL_CONFIG } from '@/config/constants'

interface SignalDetailProps {
  signal: Signal | null
  visible: boolean
  onClose: () => void
}

function OnchainSignalsDetail({ data }: { data: OnchainSignalsData | null }) {
  if (!data || Object.keys(data).length === 0) {
    return <span style={{ color: '#999' }}>无链上数据</span>
  }

  return (
    <Space size="small" wrap>
      {Object.entries(data).map(([key, value]) => {
        const config = ONCHAIN_SIGNAL_CONFIG[key as keyof typeof ONCHAIN_SIGNAL_CONFIG]
        if (!config || !value) return null

        return (
          <Tag key={key} color={config.color}>
            {config.label}
          </Tag>
        )
      })}
      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
        <div>大额转账次数: {data.large_transfer_count || '-'}</div>
        <div>交易所净流出量: {data.exchange_netflow || '-'}</div>
        <div>聪明钱净买入量: {data.smart_money_netbuy || '-'}</div>
        <div>活跃地址增长率: {data.active_address_growth || '-'}</div>
      </div>
    </Space>
  )
}

export default function SignalDetail({ signal, visible, onClose }: SignalDetailProps) {
  if (!signal) return null

  // ML置信度渲染
  const renderMLConfidence = (score: number | null) => {
    if (score === null || score === undefined) {
      return <span style={{ color: '#999' }}>-</span>
    }

    const percent = score * 100
    let strokeColor: string

    if (score >= 0.8) {
      strokeColor = '#52c41a'
    } else if (score >= 0.6) {
      strokeColor = '#1890ff'
    } else {
      strokeColor = '#faad14'
    }

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Progress 
          percent={percent} 
          size="small"
          strokeColor={strokeColor}
          format={(percent) => `${percent?.toFixed(1)}%`}
          style={{ width: 200 }}
        />
        <span style={{ fontSize: 12, color: '#666' }}>
          ({score.toFixed(4)})
        </span>
      </div>
    )
  }

  // LLM情绪渲染
  const renderLLMSentiment = (sentiment: string | null) => {
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
  }

  // 仓位权重渲染
  const renderPositionWeight = (weight: number) => {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Progress 
          percent={weight * 100} 
          size="small"
          strokeColor={{
            '0%': '#108ee9',
            '100%': '#87d068',
          }}
          format={(percent) => `${percent?.toFixed(1)}%`}
          style={{ width: 200 }}
        />
        <span style={{ fontSize: 12, color: '#666' }}>
          ({formatWeight(weight)})
        </span>
      </div>
    )
  }

  return (
    <Modal
      title="信号详情"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
    >
      <Descriptions bordered column={2} size="small">
        {/* 基本信息 */}
        <Descriptions.Item label="市场" span={1}>
          {signal.market}
        </Descriptions.Item>
        <Descriptions.Item label="信号类型" span={1}>
          <Tag color={signal.signal_type === 'PULLBACK_BUY' ? 'blue' : 'orange'}>
            {signal.signal_type}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建时间" span={2}>
          {formatDate(signal.created_at)}
        </Descriptions.Item>

        {/* 价格信息 */}
        <Descriptions.Item label="入场价" span={1}>
          {formatPrice(signal.entry_price)}
        </Descriptions.Item>
        <Descriptions.Item label="止损价" span={1}>
          {formatPrice(signal.stop_loss_price)}
        </Descriptions.Item>
        <Descriptions.Item label="目标价" span={1}>
          {formatPrice(signal.profit_target_price)}
        </Descriptions.Item>
        <Descriptions.Item label="盈亏比" span={1}>
          {signal.reward_risk_ratio ? (
            <Tag color={signal.reward_risk_ratio > 2 ? 'green' : signal.reward_risk_ratio >= 1 ? 'yellow' : 'red'}>
              {signal.reward_risk_ratio.toFixed(2)}:1
            </Tag>
          ) : '-'}
        </Descriptions.Item>

        {/* 规则引擎 */}
        <Descriptions.Item label="规则引擎评分" span={2}>
          <span style={{ fontSize: 16, fontWeight: 'bold' }}>
            {signal.rule_engine_score.toFixed(1)}
          </span>
        </Descriptions.Item>

        {/* ML引擎 */}
        <Descriptions.Item label="ML置信度" span={2}>
          {renderMLConfidence(signal.ml_confidence_score)}
        </Descriptions.Item>

        {/* LLM引擎 */}
        <Descriptions.Item label="LLM情绪" span={2}>
          {renderLLMSentiment(signal.llm_sentiment)}
        </Descriptions.Item>
        {signal.explanation && (
          <Descriptions.Item label="LLM分析" span={2}>
            <div style={{ 
              padding: 8, 
              backgroundColor: '#f5f5f5', 
              borderRadius: 4,
              fontSize: 12,
              lineHeight: 1.6
            }}>
              {signal.explanation}
            </div>
          </Descriptions.Item>
        )}

        {/* 仲裁结果 */}
        <Descriptions.Item label="最终决策" span={1}>
          {signal.final_decision ? (
            <Tag color={signal.final_decision === 'APPROVED' ? 'green' : 'red'}>
              {signal.final_decision === 'APPROVED' ? '通过' : '拒绝'}
            </Tag>
          ) : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="建议仓位权重" span={1}>
          {renderPositionWeight(signal.suggested_position_weight)}
        </Descriptions.Item>

        {/* 链上指标 */}
        {signal.onchain_signals && (
          <Descriptions.Item label="链上指标" span={2}>
            <OnchainSignalsDetail data={signal.onchain_signals} />
          </Descriptions.Item>
        )}
      </Descriptions>
    </Modal>
  )
}

