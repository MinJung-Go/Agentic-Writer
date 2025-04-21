import os
import asyncio
import gradio as gr
from main import generate_blog_post

async def generate_blog_post_wrapper(reference_text, style, api_key, model, base_url):
    """Wrapper to handle async function for Gradio"""
    os.environ["OpenAI_API_KEY"] = api_key
    os.environ["BASE_URL"] = base_url
    return await generate_blog_post(reference_text, model, style)

def run_generation(reference_text, style, api_key, model, base_url):
    """Run the async generation and return result"""
    return asyncio.run(generate_blog_post_wrapper(reference_text, style, api_key, model, base_url))

# Create Gradio interface
demo = gr.Interface(
    fn=run_generation,
    inputs=[gr.Textbox(label="参考文本", lines=10, placeholder="请输入参考文本内容..."), 
            gr.Textbox(label="风格", lines=1, placeholder="请输入风格..."),
            gr.Textbox(label="API Key", lines=1, placeholder="请输入OpenAI API Key..."),
            gr.Textbox(label="模型", lines=1, placeholder="请输入模型名称...", value="deepseek-chat"),
            gr.Textbox(label="API URL", lines=1, placeholder="请输入API URL...", value="https://api.deepseek.com/v1")
            ],
    outputs=gr.Textbox(label="生成的文章"),
    title="AI 博客文章生成器",
    description="输入参考文本，自动生成完整的博客文章"
)

if __name__ == "__main__":
    demo.launch()
