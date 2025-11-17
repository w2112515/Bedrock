import { Card, Statistic, Progress, List, Typography, Space, Alert, Spin, Row, Col, Tooltip } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { useArbitrationStats, useArbitrationConfig } from '@/hooks/useArbitration'

const { Text } = Typography

interface ArbitrationStatsCardProps {
  days?: number
}

export default function ArbitrationStatsCard({ days = 7 }: ArbitrationStatsCardProps) {
  const { data: stats, isLoading, error } = useArbitrationStats({ days })
  const { data: config } = useArbitrationConfig()

  if (isLoading) {
    return (
      <Card title={`仲裁统计（最近 ${days} 天）`}>
        <Spin />
      </Card>
    )
  }

  if (error) {
    return (
      <Card title={`仲裁统计（最近 ${days} 天）`}>
        <Alert message="加载统计数据失败" type="error" />
      </Card>
    )
  }

  if (!stats || stats.total_signals === 0) {
    return (
      <Card title={`仲裁统计（最近 ${days} 天）`}>
        <Alert message="暂无数据" type="info" />
      </Card>
    )
  }

  return (
    <Card title={`仲裁统计（最近 ${days} 天）`}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="总信号数"
              value={stats.total_signals}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="通过信号"
              value={stats.approved_signals}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="拒绝信号"
              value={stats.rejected_signals}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="通过率"
              value={stats.approval_rate}
              precision={1}
              suffix="%"
              valueStyle={{ color: stats.approval_rate >= 50 ? '#52c41a' : '#faad14' }}
            />
          </Col>
        </Row>

        <div style={{ marginTop: 16 }}>
          <Text strong>平均评分</Text>
          <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: '600px', marginTop: 8 }}>
            {/* 规则引擎 */}
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">
                  规则引擎
                  <Tooltip title="基于技术指标和趋势分析的评分（0-100）">
                    <InfoCircleOutlined style={{ marginLeft: 4, fontSize: 12, color: '#8c8c8c' }} />
                  </Tooltip>
                </Text>
              </div>
              <Progress
                percent={stats.avg_rule_score}
                strokeColor="#1890ff"
                format={(percent) => `${Math.round(percent || 0)}%`}
              />
            </div>

            {/* ML 模型 */}
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">
                  ML 模型
                  <Tooltip title="机器学习模型的置信度评分（0-100）">
                    <InfoCircleOutlined style={{ marginLeft: 4, fontSize: 12, color: '#8c8c8c' }} />
                  </Tooltip>
                </Text>
              </div>
              {stats.avg_ml_score !== null ? (
                <Progress
                  percent={stats.avg_ml_score}
                  strokeColor="#52c41a"
                  format={(percent) => `${Math.round(percent || 0)}%`}
                />
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>

            {/* LLM 情绪 */}
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">
                  LLM 情绪
                  <Tooltip title="大语言模型对市场情绪的量化评分（0-100）。基于情绪类型（BULLISH/NEUTRAL/BEARISH）和置信度计算。所有数据已使用标准算法统一计算。">
                    <InfoCircleOutlined style={{ marginLeft: 4, fontSize: 12, color: '#8c8c8c' }} />
                  </Tooltip>
                </Text>
              </div>
              {stats.avg_llm_score !== null ? (
                <Progress
                  percent={stats.avg_llm_score}
                  strokeColor="#fa8c16"
                  format={(percent) => `${Math.round(percent || 0)}%`}
                />
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>

            {/* 最终评分 */}
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">
                  最终评分
                  <Tooltip title="三个引擎的加权平均分（0-100）。权重配置见下方说明。">
                    <InfoCircleOutlined style={{ marginLeft: 4, fontSize: 12, color: '#8c8c8c' }} />
                  </Tooltip>
                </Text>
              </div>
              <Progress
                percent={stats.avg_final_score}
                strokeColor="#722ed1"
                format={(percent) => `${Math.round(percent || 0)}%`}
              />
              {config && (
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    权重配置：规则 {(config.rule_weight * 100).toFixed(0)}% | ML {(config.ml_weight * 100).toFixed(0)}% | LLM {(config.llm_weight * 100).toFixed(0)}%
                  </Text>
                </div>
              )}
            </div>
          </Space>
        </div>

        <div style={{ marginTop: 16 }}>
          <Text strong>模型一致率</Text>
          <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: '600px', marginTop: 8 }}>
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">Rule-ML 一致率</Text>
              </div>
              {stats.rule_ml_agreement_rate !== null ? (
                <Progress
                  percent={stats.rule_ml_agreement_rate}
                  format={(percent) => `${Math.round(percent || 0)}%`}
                />
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">ML-LLM 一致率</Text>
              </div>
              {stats.ml_llm_agreement_rate !== null ? (
                <Progress
                  percent={stats.ml_llm_agreement_rate}
                  format={(percent) => `${Math.round(percent || 0)}%`}
                />
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>
            <div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">Rule-LLM 一致率</Text>
              </div>
              {stats.rule_llm_agreement_rate !== null ? (
                <Progress
                  percent={stats.rule_llm_agreement_rate}
                  format={(percent) => `${Math.round(percent || 0)}%`}
                />
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>
          </Space>
        </div>

        {stats.top_rejection_reasons.length > 0 && (
          <div>
            <Text strong>Top 拒绝原因</Text>
            <List
              size="small"
              dataSource={stats.top_rejection_reasons}
              renderItem={(item) => (
                <List.Item>
                  <Text>{item.reason}</Text>
                  <Text type="secondary">({item.count} 次)</Text>
                </List.Item>
              )}
              style={{ marginTop: 8 }}
            />
          </div>
        )}
      </Space>
    </Card>
  )
}

