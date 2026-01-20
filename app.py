import streamlit as st
from tavily import TavilyClient
import google.generativeai as genai
import json
import datetime

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="AI 每日情报站 (Gemini 3.0 旗舰版)",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2026 风格界面 CSS
st.markdown("""
    <style>
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 搜索逻辑 (Tavily) ---
def search_with_tavily(tavily_key, query):
    if not tavily_key:
        st.error("❌ 请输入 Tavily API Key")
        return None
    try:
        tavily = TavilyClient(api_key=tavily_key)
        response = tavily.search(
            query=query,
            search_depth="basic",
            topic="news",            
            days=1,                  
            max_results=6
        )
        results = response.get("results", [])
        if not results: return None

        context = ""
        for idx, item in enumerate(results):
            context += f"--- Source {idx+1} ---\nTitle: {item.get('title')}\nContent: {item.get('content')}\nURL: {item.get('url')}\n"
        return context
    except Exception as e:
        st.error(f"Search Error: {e}")
        return None

# --- 3. Gemini 3.0 处理逻辑 ---
def process_news_with_gemini(google_key, raw_data, model_name):
    if not google_key:
        st.error("❌ 请输入 Google API Key")
        return None

    try:
        genai.configure(api_key=google_key)
        
        # 2026年配置：Gemini 3.0 完美支持 JSON 模式
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json"
        }

        model = genai.GenerativeModel(model_name, generation_config=generation_config)

        system_prompt = """
        You are an elite AI Tech Analyst in 2026. 
        Input: Raw search results about Artificial Intelligence.
        Task: Create a structured Daily Briefing in Simplified Chinese (简体中文).

        JSON Output Schema:
        {
            "breaking_news": [
                {"title": "CN Title", "summary": "Brief summary", "url": "URL", "source": "Source"}
            ],
            "market_analysis": [
                {"topic": "Trend Name", "insight": "Investment/Business insight"}
            ],
            "new_tech": [
                {"name": "Tool/Model Name", "desc": "What it does", "verdict": "Why it matters in 2026"}
            ]
        }
        """
        
        response = model.generate_content(system_prompt + "\n\nData:\n" + raw_data)
        return response.text

    except Exception as e:
        # 捕获具体的错误代码
        err_msg = str(e)
        if "404" in err_msg:
            st.error(f"❌ 模型未找到 (404): {model_name}。可能该区域未开放或API Key权限不足。")
        elif "429" in err_msg:
            st.error(f"❌ 配额超限 (429): {model_name} 免费版调用过于频繁。")
        else:
            st.error(f"❌ API 错误: {e}")
        return None

# --- 4. 主程序 ---
def main():
    with st.sidebar:
        st.header("⚙️ 2026 控制台")
        
        google_api_key = st.text_input("Google API Key", type="password", key="g_key")
        tavily_api_key = st.text_input("Tavily API Key", type="password", key="t_key")
        
        st.divider()
        
        # 🟢 核心修正：使用 2026 年真实的可用模型列表
        model_choice = st.selectbox(
            "选择 AI 引擎", 
            [
                "gemini-3-flash-preview",  # ⚡ 最快，2025.12发布
                "gemini-3-pro-preview",    # 🧠 最强，2025.11发布
                "gemini-2.5-flash",        # 🛡️ 稳定版 (2025年中发布)
                "gemini-2.5-pro"           # 🛡️ 稳定版 Pro
            ],
            index=0,
            help="Gemini 1.5 已于2025年退役，请使用 3.0 或 2.5 系列"
        )
        
        st.info(f"当前引擎: {model_choice}")
        run_btn = st.button("🚀 生成简报", use_container_width=True)

    st.title("🌌 AI 每日情报站 (Gen 3)")
    st.caption(f"📅 日期: {datetime.date.today()} | 🔴 核心: Google Gemini 3.0")

    if run_btn:
        if not google_api_key or not tavily_api_key:
            st.warning("⚠️ 请完善 API Key 设置")
            return

        with st.status("🔗 正在链接全球资讯网...", expanded=True) as status:
            # 1. 搜索
            status.write("🔍 Tavily 正在检索最新 AI 动态...")
            raw_news = search_with_tavily(tavily_api_key, "Artificial Intelligence news latest 24 hours Gemini 3.0 agentic workflows")
            
            if not raw_news:
                status.update(label="❌ 搜索无结果", state="error")
                return
            
            # 2. 推理
            status.write(f"⚡ 正在调用 {model_choice} 进行分析...")
            json_result = process_news_with_gemini(google_api_key, raw_news, model_choice)
            
            if not json_result:
                status.update(label="❌ 生成失败", state="error")
                return
                
            status.update(label="✅ 完成！", state="complete", expanded=False)

        # 3. 渲染
        try:
            data = json.loads(json_result)
            
            # 布局优化
            st.subheader("🚨 头条新闻 (Breaking)")
            for item in data.get("breaking_news", []):
                with st.expander(f"📰 {item['title']}", expanded=True):
                    st.write(item['summary'])
                    st.markdown(f"[阅读原文]({item['url']})")
            
            st.divider()
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📈 市场洞察")
                for m in data.get("market_analysis", []):
                    st.success(f"**{m['topic']}**\n\n{m['insight']}")
            
            with c2:
                st.subheader("🛠️ 新技术栈")
                for t in data.get("new_tech", []):
                    with st.container(border=True):
                        st.markdown(f"**{t['name']}**")
                        st.caption(t['desc'])
                        st.markdown(f"*{t['verdict']}*")

        except Exception as e:
            st.error("JSON 解析错误，请重试")
            st.code(json_result)

if __name__ == "__main__":
    main()
