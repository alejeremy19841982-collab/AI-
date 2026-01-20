import streamlit as st
from duckduckgo_search import DDGS
from openai import OpenAI
import json
import datetime

# --- 页面配置 ---
st.set_page_config(
    page_title="AI 每日情报站",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 核心逻辑函数 ---

def search_ai_news():
    """
    使用 DuckDuckGo 搜索英文高质量 AI 资讯。
    """
    query = "Artificial Intelligence news latest 24 hours breaking news tools"
    results = []
    
    try:
        with DDGS() as ddgs:
            # 获取 10 条结果以供 LLM 筛选
            ddgs_gen = ddgs.text(query, region='wt-wt', safesearch='off', max_results=10)
            for r in ddgs_gen:
                results.append(r)
    except Exception as e:
        st.error(f"❌ 搜索模块出现错误: {e}")
        return None

    if not results:
        return None
        
    # 将结果转换为字符串供 LLM 阅读
    context_text = ""
    for idx, item in enumerate(results):
        context_text += f"[{idx+1}] Title: {item.get('title')}\nSnippet: {item.get('body')}\nURL: {item.get('href')}\n\n"
    
    return context_text

def process_news_with_llm(api_key, raw_data, model_name="gpt-3.5-turbo"):
    """
    调用 OpenAI API 将英文搜索结果转化为结构化的中文日报。
    """
    client = OpenAI(api_key=api_key)
    
    # 构建 Prompt：强制要求 JSON 格式
    system_prompt = """
    You are a senior AI Tech Reporter for a Chinese audience. 
    Your goal is to read the provided English search results and generate a structured daily report in Simplified Chinese (简体中文).
    
    Output strictly valid JSON code. Do not output Markdown code blocks (like ```json). Just the raw JSON string.
    
    The JSON structure must be exactly like this:
    {
        "breaking_news": [
            {"title": "Translate title to Chinese", "summary": "Summarize in Chinese (max 50 words)", "url": "Original URL"}
        ],
        "business_insights": [
            {"insight": "Analyze a business opportunity or market trend in Chinese based on the news"}
        ],
        "new_tools": [
            {"name": "Tool Name (Keep English)", "description": "Explain what it does in Chinese"}
        ]
    }
    
    Rules:
    1. Select only the most important 3-5 news items for 'breaking_news'.
    2. Analyze 2-3 distinct business opportunities for 'business_insights'.
    3. Identify 2-3 new tools or models for 'new_tools'.
    4. Ensure all Chinese is natural, professional, and exciting.
    """

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here are the latest search results:\n{raw_data}"}
            ],
            temperature=0.7,
            response_format={"type": "json_object"} # 强制 JSON 模式（如果在 gpt-4-turbo/gpt-3.5-turbo-1106+ 上）
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"❌ LLM 处理失败: {e}")
        return None

# --- UI 渲染部分 ---

def main():
    # 侧边栏：设置与控制
    with st.sidebar:
        st.header("⚙️ 设置")
        api_key = st.text_input("OpenAI API Key", type="password", help="请输入您的 OpenAI API Key 以启动分析")
        model_choice = st.selectbox("选择模型", ["gpt-3.5-turbo", "gpt-4-turbo"])
        
        st.markdown("---")
        st.info("ℹ️ 本系统后台使用英文关键词搜索全球资讯，由大模型为您实时翻译并提炼核心情报。")
        
        generate_btn = st.button("🚀 生成今日日报", type="primary", use_container_width=True)

    # 主界面标题
    st.title("🤖 AI 每日情报站")
    st.markdown(f"**日期**: {datetime.date.today().strftime('%Y年%m月%d日')} | **状态**: 待命")
    st.markdown("---")

    if generate_btn:
        if not api_key:
            st.warning("⚠️ 请先在侧边栏输入 OpenAI API Key")
            return

        # 1. 搜索阶段
        with st.status("🔍 正在全网检索最新 AI 资讯 (DuckDuckGo)...", expanded=True) as status:
            raw_data = search_ai_news()
            
            if not raw_data:
                status.update(label="❌ 搜索失败，请检查网络连接", state="error")
                return
            
            status.write("✅ 已获取最新英文资讯源数据")
            
            # 2. LLM 处理阶段
            status.write("🧠 正在调用 LLM 进行翻译、分析与摘要...")
            json_str = process_news_with_llm(api_key, raw_data, model_choice)
            
            if not json_str:
                status.update(label="❌ 报告生成失败", state="error")
                return
            
            status.update(label="✅ 情报生成完毕！", state="complete", expanded=False)

        # 3. 数据解析与展示
        try:
            data = json.loads(json_str)
            
            # Section 1: 核心突发
            st.subheader("🚨 核心突发 (Breaking News)")
            for item in data.get("breaking_news", []):
                with st.expander(f"📰 {item['title']}", expanded=True):
                    st.markdown(f"**摘要**: {item['summary']}")
                    st.markdown(f"🔗 [阅读原文]({item['url']})")

            st.divider()

            # Section 2 & 3: 并排布局
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("💰 商业机会")
                for item in data.get("business_insights", []):
                    st.success(f"💡 {item['insight']}")

            with col2:
                st.subheader("🛠️ 新工具 / 框架")
                for tool in data.get("new_tools", []):
                    st.markdown(f"**🔧 {tool['name']}**")
                    st.caption(tool['description'])
                    st.markdown("---")

        except json.JSONDecodeError:
            st.error("解析数据格式失败，LLM 返回了非标准 JSON。请重试。")
            with st.expander("查看原始返回"):
                st.code(json_str)

if __name__ == "__main__":
    main()
