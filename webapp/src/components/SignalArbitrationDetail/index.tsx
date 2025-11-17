import { Card, Descriptions, Alert, Spin } from 'antd'
import { useArbitrationConfig } from '@/hooks/useArbitration'
import type { Signal } from '@/types/signal'

interface SignalArbitrationDetailProps {
  signal: Signal
}

export default function SignalArbitrationDetail({ signal }: SignalArbitrationDetailProps) {
  const { data: config, isLoading, error } = useArbitrationConfig()

  if (isLoading) {
    return (
      <Card title="仲裁详情" size="small">
        <Spin />
      </Card>
    )
  }

  if (error) {
    return (
      <Card title="仲裁详情" size="small">
        <Alert message="加载仲裁配置失败" type="error" />
      </Card>
    )
  }

  const getDecisionColor = (decision: string | null): 'success' | 'error' | 'info' => {
    if (!decision) return 'info'
    return decision === 'APPROVED' ? 'success' : 'error'
  }

  return (
    <Card title="仲裁详情" size="small">
      <Descriptions column={2} size="small" bordered>
        <Descriptions.Item label="规则引擎权重">
          {config?.rule_weight.toFixed(2)}
        </Descriptions.Item>
        <Descriptions.Item label="ML 模型权重">
          {config?.ml_weight.toFixed(2)}
        </Descriptions.Item>
        <Descriptions.Item label="LLM 权重">
          {config?.llm_weight.toFixed(2)}
        </Descriptions.Item>
        <Descriptions.Item label="通过阈值">
          {config?.min_approval_score.toFixed(1)} 分
        </Descriptions.Item>
        <Descriptions.Item label="自适应阈值">
          {config?.adaptive_threshold_enabled ? '启用' : '禁用'}
        </Descriptions.Item>
        <Descriptions.Item label="配置版本">
          v{config?.version}
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 16 }}>
        <Alert
          message={`最终决策：${signal.final_decision || '待定'}`}
          description={signal.explanation || '无详细说明'}
          type={getDecisionColor(signal.final_decision)}
          showIcon
        />
      </div>
    </Card>
  )
}

