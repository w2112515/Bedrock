import { Card, Progress, Tag, Typography, Space, Row, Col } from 'antd'
import type { Signal } from '@/types/signal'

const { Text } = Typography

interface SignalMlLlmComparisonProps {
  signal: Signal
}

export default function SignalMlLlmComparison({ signal }: SignalMlLlmComparisonProps) {
  const mlScore = signal.ml_confidence_score
  const llmSentiment = signal.llm_sentiment
  const ruleScore = signal.rule_engine_score

  const getSentimentColor = (sentiment: string | null) => {
    if (!sentiment) return 'default'
    switch (sentiment) {
      case 'BULLISH':
        return 'success'
      case 'BEARISH':
        return 'error'
      case 'NEUTRAL':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#52c41a'
    if (score >= 60) return '#1890ff'
    return '#faad14'
  }

  return (
    <Card title="模型评分对比" size="small">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Row gutter={16}>
          <Col span={8}>
            <div>
              <Text type="secondary">规则引擎</Text>
              <div style={{ marginTop: 8 }}>
                <Progress
                  percent={ruleScore}
                  strokeColor={getScoreColor(ruleScore)}
                  format={(percent) => `${percent?.toFixed(1)}分`}
                />
              </div>
            </div>
          </Col>

          <Col span={8}>
            <div>
              <Text type="secondary">ML 置信度</Text>
              <div style={{ marginTop: 8 }}>
                {mlScore !== null ? (
                  <Progress
                    percent={mlScore * 100}
                    strokeColor={getScoreColor(mlScore * 100)}
                    format={(percent) => `${percent?.toFixed(1)}%`}
                  />
                ) : (
                  <Text type="secondary">-</Text>
                )}
              </div>
            </div>
          </Col>

          <Col span={8}>
            <div>
              <Text type="secondary">LLM 情绪</Text>
              <div style={{ marginTop: 8 }}>
                {llmSentiment ? (
                  <Tag color={getSentimentColor(llmSentiment)}>
                    {llmSentiment}
                  </Tag>
                ) : (
                  <Text type="secondary">-</Text>
                )}
              </div>
            </div>
          </Col>
        </Row>
      </Space>
    </Card>
  )
}

