import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  SignalFilled,
  ExperimentOutlined,
  WalletOutlined,
  TransactionOutlined
} from '@ant-design/icons'
import { queryClient } from '@/config/queryClient'
import ErrorBoundary from '@/components/ErrorBoundary'
import Dashboard from '@/pages/Dashboard'
import Signals from '@/pages/Signals'
import Backtest from '@/pages/Backtest'
import Positions from '@/pages/Positions'
import Trades from '@/pages/Trades'
import { validateEnv } from '@/config/env'

const { Header, Content, Sider } = Layout

validateEnv()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Layout style={{ minHeight: '100vh' }}>
            <Header style={{ 
              display: 'flex', 
              alignItems: 'center',
              background: '#001529',
              color: '#fff',
              padding: '0 24px'
            }}>
              <h2 style={{ color: '#fff', margin: 0 }}>Project Bedrock</h2>
            </Header>
            <Layout>
              <Sider width={200} style={{ background: '#fff' }}>
                <Menu
                  mode="inline"
                  defaultSelectedKeys={['dashboard']}
                  style={{ height: '100%', borderRight: 0 }}
                >
                  <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
                    <Link to="/">仪表盘</Link>
                  </Menu.Item>
                  <Menu.Item key="signals" icon={<SignalFilled />}>
                    <Link to="/signals">交易信号</Link>
                  </Menu.Item>
                  <Menu.Item key="backtest" icon={<ExperimentOutlined />}>
                    <Link to="/backtest">回测管理</Link>
                  </Menu.Item>
                  <Menu.Item key="positions" icon={<WalletOutlined />}>
                    <Link to="/positions">持仓管理</Link>
                  </Menu.Item>
                  <Menu.Item key="trades" icon={<TransactionOutlined />}>
                    <Link to="/trades">交易历史</Link>
                  </Menu.Item>
                </Menu>
              </Sider>
              <Layout style={{ padding: '0' }}>
                <Content style={{ 
                  background: '#f0f2f5',
                  minHeight: 280 
                }}>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/signals" element={<Signals />} />
                    <Route path="/backtest" element={<Backtest />} />
                    <Route path="/positions" element={<Positions />} />
                    <Route path="/trades" element={<Trades />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Content>
              </Layout>
            </Layout>
          </Layout>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  )
}

export default App

