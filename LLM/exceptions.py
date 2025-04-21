class OpenAIError(Exception):
    """基础异常类"""
    def __init__(self, message=None, http_status=None, response=None):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.response = response

class APIError(OpenAIError):
    """API错误"""
    pass

class APIConnectionError(OpenAIError):
    """API连接错误"""
    pass

class InvalidRequestError(OpenAIError):
    """无效请求错误"""
    pass

class AuthenticationError(OpenAIError):
    """认证错误"""
    pass

class RateLimitError(OpenAIError):
    """速率限制错误"""
    pass