#!/usr/bin/env python3
"""
AI平台适配器工厂
"""

from typing import Dict, Any
from .base_adapter import BaseAIAdapter
from .dify_adapter import DifyAdapter
from .coze_adapter import CozeAdapter
from .n8n_adapter import N8NAdapter

class AdapterFactory:
    """AI平台适配器工厂"""
    
    _adapters = {
        'dify': DifyAdapter,
        'coze': CozeAdapter,
        'n8n': N8NAdapter,
    }
    
    @classmethod
    def create_adapter(cls, platform_type: str, config: Dict[str, Any]) -> BaseAIAdapter:
        """
        创建AI平台适配器
        
        Args:
            platform_type: 平台类型 ('dify', 'coze', 'n8n')
            config: 平台配置
        
        Returns:
            BaseAIAdapter: 适配器实例
        
        Raises:
            ValueError: 不支持的AI平台类型
        """
        if platform_type not in cls._adapters:
            raise ValueError(f"不支持的AI平台类型: {platform_type}")
        
        adapter_class = cls._adapters[platform_type]
        adapter = adapter_class(config)
        
        if not adapter.validate_config():
            raise ValueError(f"{platform_type}配置不完整")
        
        return adapter
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """获取支持的平台列表"""
        return list(cls._adapters.keys())
    
    @classmethod
    def register_adapter(cls, platform_type: str, adapter_class):
        """注册新的平台适配器"""
        cls._adapters[platform_type] = adapter_class