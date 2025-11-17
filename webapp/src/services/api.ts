import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'antd'
import { env } from '@/config/env'

function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function createApiInstance(baseURL: string, serviceName: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: env.apiTimeout,
    headers: {
      'Content-Type': 'application/json'
    }
  })

  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const requestId = generateRequestId()
      config.headers['X-Request-ID'] = requestId
      
      if (env.debug) {
        console.log(`[${serviceName}] Request:`, {
          method: config.method?.toUpperCase(),
          url: config.url,
          requestId,
          params: config.params,
          data: config.data
        })
      }
      
      return config
    },
    (error: AxiosError) => {
      console.error(`[${serviceName}] Request Error:`, error)
      return Promise.reject(error)
    }
  )

  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      if (env.debug) {
        console.log(`[${serviceName}] Response:`, {
          status: response.status,
          requestId: response.config.headers['X-Request-ID'],
          data: response.data
        })
      }
      
      return response
    },
    (error: AxiosError) => {
      handleApiError(error, serviceName)
      return Promise.reject(error)
    }
  )

  return instance
}

function handleApiError(error: AxiosError, serviceName: string) {
  const requestId = error.config?.headers?.['X-Request-ID']

  if (error.response) {
    const { status, data } = error.response

    switch (status) {
      case 400:
        message.error({
          content: `请求参数错误: ${(data as any)?.detail || '未知错误'}`,
          key: 'api-error-400',
          duration: 3
        })
        break
      case 401:
        message.error({
          content: '未授权，请登录',
          key: 'api-error-401',
          duration: 3
        })
        break
      case 403:
        message.error({
          content: '权限不足',
          key: 'api-error-403',
          duration: 3
        })
        break
      case 404:
        message.error({
          content: '请求的资源不存在',
          key: 'api-error-404',
          duration: 3
        })
        break
      case 500:
        message.error({
          content: `服务器错误: ${(data as any)?.detail || '未知错误'}`,
          key: 'api-error-500',
          duration: 3
        })
        break
      case 503:
        message.error({
          content: '服务暂时不可用，请稍后重试',
          key: 'api-error-503',
          duration: 3
        })
        break
      default:
        message.error({
          content: `请求失败 (${status}): ${(data as any)?.detail || '未知错误'}`,
          key: `api-error-${status}`,
          duration: 3
        })
    }

    console.error(`[${serviceName}] API Error:`, {
      status,
      requestId,
      url: error.config?.url,
      data
    })
  } else if (error.request) {
    message.error({
      content: '网络错误，请检查网络连接',
      key: 'network-error',
      duration: 3
    })
    console.error(`[${serviceName}] Network Error:`, {
      requestId,
      url: error.config?.url
    })
  } else {
    message.error({
      content: `请求配置错误: ${error.message}`,
      key: 'config-error',
      duration: 3
    })
    console.error(`[${serviceName}] Config Error:`, error.message)
  }
}

export const dataHubApi = createApiInstance(env.dataHubBaseUrl, 'DataHub')
export const decisionEngineApi = createApiInstance(env.decisionEngineBaseUrl, 'DecisionEngine')
export const portfolioApi = createApiInstance(env.portfolioBaseUrl, 'Portfolio')
export const backtestingApi = createApiInstance(env.backtestingBaseUrl, 'Backtesting')

export type { AxiosInstance, AxiosError, AxiosResponse }

