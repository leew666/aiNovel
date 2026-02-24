"""
LLM接入层单元测试

使用Mock测试各客户端的核心功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ainovel.llm import (
    OpenAIClient,
    ClaudeClient,
    QwenClient,
    LLMFactory,
    LLMConfig,
    APIKeyError,
    TokenLimitError,
    RateLimitError,
)
from ainovel.llm.base import BaseLLMClient


class TestLLMConfig:
    """测试LLM配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.daily_budget == 5.0

    def test_custom_provider_allowed(self):
        """测试自定义provider可被保留"""
        config = LLMConfig(provider="invalid_provider")
        assert config.provider == "invalid_provider"

    def test_temperature_range(self):
        """测试temperature范围"""
        with pytest.raises(ValueError):
            LLMConfig(temperature=1.5)
        with pytest.raises(ValueError):
            LLMConfig(temperature=-0.1)

    @patch.dict("os.environ", {"DEFAULT_LLM_PROVIDER": "claude", "DEFAULT_TEMPERATURE": "0.8"})
    def test_from_env(self):
        """测试从环境变量加载"""
        config = LLMConfig.from_env()
        assert config.provider == "claude"
        assert config.temperature == 0.8


class TestOpenAIClient:
    """测试OpenAI客户端"""

    def test_init_without_key(self):
        """测试无API密钥初始化"""
        with pytest.raises(APIKeyError):
            OpenAIClient(api_key="")

    @patch("ainovel.llm.openai_client.OpenAI")
    def test_generate_success(self, mock_openai):
        """测试成功生成"""
        # Mock响应
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="测试回复"))]
        mock_response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        mock_response.model = "gpt-4o-mini"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # 测试
        client = OpenAIClient(api_key="test_key")
        result = client.generate([{"role": "user", "content": "你好"}])

        assert result["content"] == "测试回复"
        assert result["usage"]["input_tokens"] == 10
        assert result["usage"]["output_tokens"] == 20
        assert result["cost"] > 0

    def test_count_tokens(self):
        """测试Token计数"""
        client = OpenAIClient(api_key="test_key")
        tokens = client.count_tokens("Hello, world!")
        assert tokens > 0

    def test_estimate_cost(self):
        """测试成本估算"""
        client = OpenAIClient(api_key="test_key", model="gpt-4o-mini")
        cost = client.estimate_cost(1000, 1000)
        # gpt-4o-mini: input $0.00015/1k, output $0.0006/1k
        expected = (1000 / 1000) * 0.00015 + (1000 / 1000) * 0.0006
        assert abs(cost - expected) < 0.0001

    def test_capabilities(self):
        """测试能力声明"""
        client = OpenAIClient(api_key="test_key", model="gpt-4o-mini")
        caps = client.get_capabilities()
        assert caps["json_mode"] is True
        assert caps["structured_output"] is True


class TestClaudeClient:
    """测试Claude客户端"""

    def test_init_without_key(self):
        """测试无API密钥初始化"""
        with pytest.raises(APIKeyError):
            ClaudeClient(api_key="")

    @patch("ainovel.llm.claude_client.Anthropic")
    def test_generate_success(self, mock_anthropic):
        """测试成功生成"""
        # Mock响应
        mock_response = Mock()
        mock_response.content = [Mock(text="测试回复")]
        mock_response.usage = Mock(
            input_tokens=10,
            output_tokens=20,
        )
        mock_response.model = "claude-3-haiku-20240307"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # 测试
        client = ClaudeClient(api_key="test_key")
        result = client.generate([{"role": "user", "content": "你好"}])

        assert result["content"] == "测试回复"
        assert result["usage"]["input_tokens"] == 10
        assert result["usage"]["output_tokens"] == 20

    def test_estimate_cost(self):
        """测试成本估算"""
        client = ClaudeClient(api_key="test_key", model="claude-3-haiku-20240307")
        cost = client.estimate_cost(1000, 1000)
        # claude-3-haiku: input $0.00025/1k, output $0.00125/1k
        expected = (1000 / 1000) * 0.00025 + (1000 / 1000) * 0.00125
        assert abs(cost - expected) < 0.0001

    def test_capabilities(self):
        """测试能力声明"""
        client = ClaudeClient(api_key="test_key", model="claude-3-haiku-20240307")
        caps = client.get_capabilities()
        assert caps["json_mode"] is False
        assert caps["structured_output"] is True


class TestQwenClient:
    """测试通义千问客户端"""

    def test_init_without_key(self):
        """测试无API密钥初始化"""
        with pytest.raises(APIKeyError):
            QwenClient(api_key="")

    def test_count_tokens(self):
        """测试Token计数(粗略估计)"""
        client = QwenClient(api_key="test_key")
        tokens = client.count_tokens("你好世界")
        # 粗略估计: len("你好世界") = 4, 4 // 2 = 2
        assert tokens == 2

    def test_estimate_cost(self):
        """测试成本估算"""
        client = QwenClient(api_key="test_key", model="qwen-max")
        cost = client.estimate_cost(1000, 1000)
        # qwen-max: ¥0.02/1k tokens (input+output)
        expected = (1000 / 1000) * 0.02 + (1000 / 1000) * 0.02
        assert abs(cost - expected) < 0.001


class DummyProviderClient(BaseLLMClient):
    """用于注册测试的模拟 Provider 客户端"""

    def generate(self, messages, temperature=0.7, max_tokens=2000, **kwargs):
        return {
            "content": "dummy",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "cost": 0.0,
            "model": self.model,
        }

    def count_tokens(self, text: str) -> int:
        return len(text)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0


class TestLLMFactory:
    """测试LLM工厂"""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test_openai_key"})
    def test_create_openai_client(self):
        """测试创建OpenAI客户端"""
        client = LLMFactory.create_client(provider="openai")
        assert isinstance(client, OpenAIClient)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_claude_key"})
    def test_create_claude_client(self):
        """测试创建Claude客户端"""
        client = LLMFactory.create_client(provider="claude")
        assert isinstance(client, ClaudeClient)

    @patch.dict("os.environ", {"DASHSCOPE_API_KEY": "test_qwen_key"})
    def test_create_qwen_client(self):
        """测试创建Qwen客户端"""
        client = LLMFactory.create_client(provider="qwen")
        assert isinstance(client, QwenClient)

    def test_create_without_key(self):
        """测试无API密钥创建"""
        with pytest.raises(APIKeyError):
            LLMFactory.create_client(provider="openai")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"})
    def test_client_cache(self):
        """测试客户端缓存"""
        LLMFactory.clear_cache()
        client1 = LLMFactory.create_client(provider="openai")
        client2 = LLMFactory.create_client(provider="openai")
        # 应该返回同一个实例
        assert client1 is client2

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"})
    def test_register_provider(self):
        """测试动态注册 provider"""
        LLMFactory.register_provider(
            "dummy",
            DummyProviderClient,
            api_key_field="openai_api_key",
            uses_openai_base=False,
        )
        LLMFactory.clear_cache()
        client = LLMFactory.create_client(provider="dummy", model="dummy-model")
        assert isinstance(client, DummyProviderClient)

    def test_get_registered_providers(self):
        """测试获取已注册提供商"""
        providers = LLMFactory.get_registered_providers()
        assert "openai" in providers
        assert "claude" in providers
        assert "qwen" in providers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
