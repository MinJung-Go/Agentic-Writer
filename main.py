import os
import click
import asyncio
from typing import List
from LLM import OpenAIClient
from agents import OutlineAgent, ContentAgent, PolishAgent

async def generate_blog_post(reference_text: str, model: str = "deepseek-chat", style: str = "微信公众号百万大V") -> str:
    """
    使用多Agent系统生成一篇完整的博客文章。
    
    Args:
        reference_text: 参考文本内容
        
    Returns:
        生成并润色后的完整博客文章
    """
    # 初始化 LLM 客户端
    llm = OpenAIClient(base_url=os.environ.get("BASE_URL"), api_key=os.environ.get("OpenAI_API_KEY"))
    
    # 初始化三个Agent
    outline_agent = OutlineAgent(llm)
    content_agent = ContentAgent(llm)
    polish_agent = PolishAgent(llm)
    
    print("1. 正在生成文章大纲...")
    sections, prompts = await outline_agent.generate_outline(reference_text, model = model)
    
    print("\n生成的大纲：")
    for i, section in enumerate(sections, 1):
        print(f"{i}. {section}")
    
    print("\n2. 正在生成各部分内容...")
    # 以并发的方式来调用generate_content方法，以便同时生成所有部分的内容，并将其保存到section_contents列表中
    # section_contents = await asyncio.gather(*[content_agent.generate_content(section, reference_text, prompt) for section, prompt in zip(sections, prompts)])
    
    section_contents = []
    for i, (section, prompt) in enumerate(zip(sections, prompts), 1):
        print(f"\n生成第 {i} 部分: {section}")
        content = await content_agent.generate_content(section, reference_text, prompt, model=model)
        section_contents.append(f"## {section}\n\n{content}")
    
    # # 组合所有内容
    # full_content = "\n\n".join(section_contents)
    
    print("\n3. 正在润色文章...")
    for section_content_idx in range(len(section_contents)):
        full_content = "\n\n".join(section_contents[:section_content_idx])
        section_content = section_contents[section_content_idx]
        polished_section_content = await polish_agent.polish_content(full_content, section_content, reference_text, model=model)
        section_contents[section_content_idx] = polished_section_content
        print(f"润色第 {section_content_idx + 1} 部分完成.")
    # polished_content = await polish_agent.polish_content(full_content)

    polished_content = "\n\n".join(section_contents)
    
    return polished_content

@click.command()
@click.option("--api_key")
@click.option(
    "--file",
    help="txt文件地址",
)
@click.option(
    "--output",
    help="生成的文件保存地址",
)
@click.option(
    "--model",
    default="deepseek-chat",
    help="模型名称",
)
@click.option(
    "--base_url",
    default="https://api.deepseek.com/v1",
    help="API URL",
)
@click.option(
    "--style",
    default="逻辑清晰，简单易懂，微信公众号，中文",
    help="风格名称",
)

def main(api_key: str, file: str, style: str, output: str, model: str, base_url: str):
    # 设置API密钥

    os.environ["OpenAI_API_KEY"] = api_key  # 请替换为您的API密钥
    os.environ["BASE_URL"] = base_url
    
    # 示例参考文本
    # reference_text = """
    # 这里是您的参考文本内容。
    # 可以是任何与您想要生成的博客相关的文本材料。
    # 可以包含行业信息、研究数据、案例分析等。
    # """
    # 打开2503.07598v2.txt到reference_text
    with open(file,'r', encoding='utf-8') as f:
        reference_text = f.read()

    final_article = asyncio.run(generate_blog_post(reference_text, model=model, style=style))
    # 保存final_article到result.txt文件中
    with open(output, 'w',encoding="utf-8") as f:
        f.write(str(final_article))
    
    print("\n最终生成的文章：")
    print("=" * 50)
    print(final_article)
    print("=" * 50)
        
    # except Exception as e:
    #     print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()