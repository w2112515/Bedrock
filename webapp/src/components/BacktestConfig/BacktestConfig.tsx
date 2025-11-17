import { Card, Form, Row, Col, Select, DatePicker, InputNumber, Button, message } from 'antd'
import { useCreateBacktest } from '@/hooks/useBacktests'
import type { CreateBacktestRequest } from '@/types/backtest'
import { STRATEGY_OPTIONS, MARKET_OPTIONS, INTERVAL_OPTIONS } from '@/types/backtest'

interface BacktestConfigProps {
  onSubmitSuccess?: () => void
}

export default function BacktestConfig({ onSubmitSuccess }: BacktestConfigProps) {
  const [form] = Form.useForm()
  const { mutate: createBacktest, isPending } = useCreateBacktest()

  const handleSubmit = (values: any) => {
    const [startDate, endDate] = values.date_range
    
    const requestData: CreateBacktestRequest = {
      strategy_name: values.strategy_name,
      market: values.market,
      interval: values.interval,
      start_date: startDate.format('YYYY-MM-DD'),
      end_date: endDate.format('YYYY-MM-DD'),
      initial_balance: values.initial_balance
    }
    
    createBacktest(requestData, {
      onSuccess: () => {
        message.success('回测任务创建成功')
        form.resetFields()
        onSubmitSuccess?.()
      },
      onError: (error: any) => {
        message.error(`创建失败: ${error.message || '未知错误'}`)
      }
    })
  }

  return (
    <Card title="创建回测任务" style={{ marginBottom: 24 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          interval: '1h',
          initial_balance: 100000
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="strategy_name"
              label="策略"
              rules={[{ required: true, message: '请选择策略' }]}
            >
              <Select
                placeholder="选择策略"
                options={STRATEGY_OPTIONS}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="market"
              label="市场"
              rules={[{ required: true, message: '请选择市场' }]}
            >
              <Select
                showSearch
                placeholder="选择交易对"
                options={MARKET_OPTIONS}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              />
            </Form.Item>
          </Col>
        </Row>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="interval"
              label="时间间隔"
              rules={[{ required: true, message: '请选择时间间隔' }]}
            >
              <Select
                placeholder="选择时间间隔"
                options={INTERVAL_OPTIONS}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="date_range"
              label="日期范围"
              rules={[
                { required: true, message: '请选择日期范围' },
                {
                  validator: (_, value) => {
                    if (!value || !value[0] || !value[1]) {
                      return Promise.reject('请选择完整的日期范围')
                    }
                    const [start, end] = value
                    if (end.isBefore(start)) {
                      return Promise.reject('结束日期不能早于开始日期')
                    }
                    if (end.diff(start, 'days') < 1) {
                      return Promise.reject('日期范围至少为1天')
                    }
                    return Promise.resolve()
                  }
                }
              ]}
            >
              <DatePicker.RangePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="initial_balance"
              label="初始余额"
              rules={[
                { required: true, message: '请输入初始余额' },
                { type: 'number', min: 1000, message: '初始余额不能少于1000 USDT' },
                { type: 'number', max: 10000000, message: '初始余额不能超过10000000 USDT' }
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                addonAfter="USDT"
                placeholder="输入初始余额"
                min={1000}
                max={10000000}
              />
            </Form.Item>
          </Col>
        </Row>
        
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={isPending}>
            创建回测任务
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}

