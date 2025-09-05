import type { EmailCodeDTO, LoginDTO, LoginVO, RegisterDTO } from './types';
import { get, post } from '@/utils/request';

export const login = (data: LoginDTO) => post<LoginVO>('/auth/login', data).json();

// 邮箱验证码
export const emailCode = (data: EmailCodeDTO) => post('/auth/email/code', data).json();

// 注册账号
export const register = (data: RegisterDTO) => post('/auth/register', data).json();

// 获取用户信息
export const getUserInfo = () => get<LoginVO>('/auth/info').json();

// 用户登出
export const logout = () => post('/auth/logout').json();
