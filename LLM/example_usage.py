import os
import sys
from LLM import OpenAIClient, OpenAIError, APIError, AuthenticationError

async def main():
    # 设置API密钥
    os.environ["OpenAI_API_KEY"] = "*******"
    
    LLM = OpenAIClient(base_url="https://api.deepseek.com/v1", api_key=os.environ.get("OpenAI_API_KEY"))
    messages=[
                {
                    "role": "user",
                    "content": "Say this is a test",
                }
            ]
    response = await LLM(messages, model="deepseek-chat", temperature=0.7)
    print(response)
    

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())