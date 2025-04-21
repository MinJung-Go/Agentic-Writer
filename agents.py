import os
import sys
from typing import List, Dict, Any
from LLM import OpenAIClient, OpenAIError, APIError, AuthenticationError

class BaseAgent:
    def __init__(self, llm_client: OpenAIClient):
        self.llm = llm_client

    async def _call_llm(self, messages: List[Dict[str, str]], temperature: float = 0.3, model: str = "deepseek-chat") -> str:
        try:
            response = await self.llm(messages, model=model, temperature=temperature)
            return response.choices[0].message.content
        except (OpenAIError, APIError, AuthenticationError) as e:
            print(f"Error calling LLM: {str(e)}")
            return ""

class OutlineAgent(BaseAgent):
    async def generate_outline(self, reference_text: str, temperature: float = 0.5, model: str = "deepseek-chat", style: str = "") -> tuple[List[str], List[str]]:
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的文章大纲规划专家。你需要基于参考文本生成一个结构清晰的博客大纲，并为每个部分提供写作建议。"
            },
            {
                "role": "user",
                "content": f"""请基于以下参考文本生成一个博客大纲，并为每个部分提供详细的写作提示：
风格选择：
{style}

参考文本：
{reference_text}

请按照以下格式输出：
大纲：
1. [大纲标题1]
2. [大纲标题2]
...

写作提示：
1. [对应大纲1的写作提示]
2. [对应大纲2的写作提示]
...
"""
            }
        ]
        
        response = await self._call_llm(messages, temperature = temperature, model = model)
        
        # 解析响应，提取大纲和写作提示
        sections = []
        prompts = []
        
        try:
            parts = response.split("写作提示：")
            outline_part = parts[0].split("大纲：")[1].strip()
            prompts_part = parts[1].strip()
            
            sections = [line.strip()[3:].strip() for line in outline_part.split("\n") if line.strip() and line[0].isdigit()]
            prompts = [line.strip()[3:].strip() for line in prompts_part.split("\n") if line.strip() and line[0].isdigit()]
        except Exception as e:
            print(f"Error parsing outline: {str(e)}")
        
        return sections, prompts

class ContentAgent(BaseAgent):
    async def generate_content(self, outline: str, reference_text: str, writing_prompt: str, temperature: float = 0.3, model: str = "deepseek-chat") -> str:
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的内容写作专家，擅长以严谨和通俗易懂的方式写微信公众号和知乎的博客。你需要基于大纲、参考文本和写作提示生成高质量的内容。"
            },
            {
                "role": "user",
                "content": f"""请基于以下信息生成内容：

大纲部分：{outline}

参考文本：
{reference_text}

写作提示：
{writing_prompt}

请生成这个部分的详细内容，确保内容与大纲主题相关，并充分利用参考文本的信息。
"""
            }
        ]
        
        return await self._call_llm(messages, temperature = temperature, model = model)

class PolishAgent(BaseAgent):
    async def polish_content(self, content: str, section_content: str, article: str,  temperature: float = 0.3, model: str = "deepseek-chat") -> str:
        messages = [
            {
                "role": "system",
                "content": "你是一个顶级的公众号大V，擅长写文章和审稿。你需要对内容进行审阅和润色，提升其可读性和专业性和严谨性，降低重复度，但保持原有的核心信息不变。"
            },
            {
                "role": "user",
                "content": f"""参考【参考文本】先对【当前章节】进行修改，删除逻辑性和事实不符类错误；然后请结合【全文章节】对【当前章节】进行润色，提升其表达质量：

【参考文本】
{article}
                
【全文章节】
{content}

【当前章节】
{section_content}

请注意：
1. 保持原有的核心信息不变
2. 提升语言的流畅性和专业性
3. 优化段落结构和过渡，并去除冗余的地方
4. 确保内容的连贯性和逻辑性
5. 给上插图建议，在每个段落后面给上建议插图，用（）括起来
6. 检查生成文本的相对【参考文本】的准确度，并基于【参考文本】来进行修正
"""
            }
        ]
        
        return await self._call_llm(messages, temperature = temperature, model = model)