import os
import time
import json
import requests
from typing import List, Dict, Optional, Union, Any, Iterator
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Message:
    """消息对象"""
    content: str
    role: str

@dataclass
class Delta:
    """流式响应中的增量内容"""
    content: Optional[str] = None
    role: Optional[str] = None

@dataclass
class Choice:
    """选择对象"""
    message: Message
    index: int
    finish_reason: Optional[str] = None
    
    # 用于流式响应
    delta: Optional[Delta] = None

@dataclass
class Usage:
    """使用情况统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

@dataclass
class ChatCompletion:
    """聊天补全响应对象"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None

class APIError(Exception):
    """API错误基类"""
    def __init__(self, message=None, http_status=None, response=None):
        self.message = message
        self.http_status = http_status
        self.response = response
        super().__init__(self.message)

class RateLimitError(APIError):
    """速率限制错误"""
    pass

class AuthenticationError(APIError):
    """认证错误"""
    pass

class BadRequestError(APIError):
    """请求错误"""
    pass

class Completions:
    """补全API类"""
    def __init__(self, client):
        self.client = client

    def create(
        self,
        messages: List[Dict[str, str]],
        model: str = "OpenAI-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ChatCompletion, Iterator[ChatCompletion]]:
        """
        创建聊天补全
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数(0-1)
            max_tokens: 最大生成token数
            stream: 是否启用流式输出
            **kwargs: 其他参数
            
        Returns:
            ChatCompletion或Iterator[ChatCompletion]: 聊天补全响应或流式响应迭代器
        """
        url = f"{self.client.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.client.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        if max_tokens is not None:
            data["max_tokens"] = max_tokens
            
        try:
            if stream:
                return self._handle_streaming_response(url, headers, data)
            else:
                return self._handle_standard_response(url, headers, data)
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e)
    
    def _handle_standard_response(self, url, headers, data) -> ChatCompletion:
        """处理标准响应"""
        response = requests.post(url, headers=headers, json=data)
        self._check_response_error(response)
        
        response_data = response.json()
        
        # 构造响应对象
        choices = []
        for choice_data in response_data.get("choices", []):
            message_data = choice_data.get("message", {})
            message = Message(
                content=message_data.get("content", ""),
                role=message_data.get("role", "assistant")
            )
            
            choice = Choice(
                message=message,
                index=choice_data.get("index", 0),
                finish_reason=choice_data.get("finish_reason")
            )
            choices.append(choice)
            
        usage_data = response_data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        ) if usage_data else None
            
        return ChatCompletion(
            id=response_data.get("id", ""),
            object=response_data.get("object", "chat.completion"),
            created=response_data.get("created", int(time.time())),
            model=response_data.get("model", data["model"]),
            choices=choices,
            usage=usage
        )
    
    def _handle_streaming_response(self, url, headers, data) -> Iterator[ChatCompletion]:
        """处理流式响应"""
        response = requests.post(url, headers=headers, json=data, stream=True)
        self._check_response_error(response)
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    line = line[6:]  # 移除 'data: ' 前缀
                    
                if line == "[DONE]":
                    break
                    
                try:
                    response_data = json.loads(line)
                    
                    # 构造增量响应对象
                    choices = []
                    for choice_data in response_data.get("choices", []):
                        delta_data = choice_data.get("delta", {})
                        delta = Delta(
                            content=delta_data.get("content"),
                            role=delta_data.get("role")
                        )
                        
                        # 为了保持与非流式API一致的接口，我们也创建一个message
                        message = Message(
                            content=delta_data.get("content", ""),
                            role=delta_data.get("role", "assistant")
                        )
                        
                        choice = Choice(
                            message=message,
                            delta=delta,
                            index=choice_data.get("index", 0),
                            finish_reason=choice_data.get("finish_reason")
                        )
                        choices.append(choice)
                        
                    yield ChatCompletion(
                        id=response_data.get("id", ""),
                        object=response_data.get("object", "chat.completion.chunk"),
                        created=response_data.get("created", int(time.time())),
                        model=response_data.get("model", data["model"]),
                        choices=choices
                    )
                    
                except json.JSONDecodeError:
                    continue
    
    def _check_response_error(self, response):
        """检查响应错误"""
        if response.status_code == 200:
            return
            
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except:
            error_message = f"HTTP {response.status_code} error"
            
        if response.status_code == 401:
            raise AuthenticationError(error_message, response.status_code, response)
        elif response.status_code == 429:
            raise RateLimitError(error_message, response.status_code, response)
        elif response.status_code == 400:
            raise BadRequestError(error_message, response.status_code, response)
        else:
            raise APIError(error_message, response.status_code, response)
    
    def _handle_request_error(self, exception):
        """处理请求错误"""
        if hasattr(exception, 'response') and exception.response is not None:
            self._check_response_error(exception.response)
        raise APIError(str(exception))

class Chat:
    """聊天API类"""
    def __init__(self, client):
        self.completions = Completions(client)

class OpenAI:
    """OpenAI客户端（OpenAI风格）"""
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1"
    ):
        self.api_key = api_key or os.environ.get("OpenAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either as an argument or via OpenAI_API_KEY environment variable")
            
        self.base_url = base_url
        self.chat = Chat(self)
    
    # 创建__call__方法，用于实现客户端的调用行为，支持Fucntion callable 协议
    async def __call__(self, 
                        messages: List[Message], 
                        functions: List[Dict[str, Any]] = None, 
                        model: str = "OpenAI-chat", 
                        temperature: float = 0.5, 
                        max_tokens: int = None, **kwargs) -> Union[ChatCompletion, Iterator[ChatCompletion]]:
        
        return self.chat.completions.create(
            messages=messages,
            functions=functions,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        

# 使用示例
def main():
    # 创建客户端实例
    client = OpenAI(api_key=os.environ.get("OpenAI_API_KEY", "your-api-key-here"))

    # 示例1：标准调用
    try:
        print("=== 标准调用示例 ===")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的AI助手。"
                },
                {
                    "role": "user",
                    "content": "请简要介绍人工智能的发展历史。"
                }
            ],
            model="OpenAI-chat",
        )
        
        print(f"ID: {chat_completion.id}")
        print(f"模型: {chat_completion.model}")
        print(f"内容: {chat_completion.choices[0].message.content}")
        
        if chat_completion.usage:
            print(f"Token使用: {chat_completion.usage.total_tokens}")
    
    except Exception as e:
        print(f"标准调用错误: {e}")
    
    # 示例2：流式调用
    try:
        print("\n=== 流式调用示例 ===")
        stream = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "请写一首关于AI的短诗。"
                }
            ],
            model="OpenAI-chat",
            stream=True
        )
        
        full_content = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_piece = chunk.choices[0].delta.content
                full_content += content_piece
                print(content_piece, end="", flush=True)
        
        print("\n\n完整内容:")
        print(full_content)
        
    except Exception as e:
        print(f"流式调用错误: {e}")

if __name__ == "__main__":
    main()
