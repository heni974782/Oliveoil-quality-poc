const SESSION_KEY = 'olive_api_token'

export const getToken = (): string => sessionStorage.getItem(SESSION_KEY) ?? ''

export const setToken = (token: string): void => sessionStorage.setItem(SESSION_KEY, token)

export const clearToken = (): void => sessionStorage.removeItem(SESSION_KEY)
