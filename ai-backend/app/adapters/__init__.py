#!/usr/bin/env python3
"""
AI平台适配器模块
支持多平台智能体统一接口
"""

from .base_adapter import BaseAIAdapter
from .dify_adapter import DifyAdapter
from .coze_adapter import CozeAdapter
from .n8n_adapter import N8NAdapter
from .adapter_factory import AdapterFactory

__all__ = [
    "BaseAIAdapter",
    "DifyAdapter", 
    "CozeAdapter",
    "N8NAdapter",
    "AdapterFactory"
]