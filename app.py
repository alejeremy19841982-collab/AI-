import streamlit as st
from tavily import TavilyClient
import google.generativeai as genai
import json
import datetime

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="AI 每日情报站 (Tavily版)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 美化
st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 搜索逻辑 (Tavily 引擎) ---
def search_with_tavily(tavily_key, query):
    """
    使用 Tavily 搜索，这是专为 LLM 设计的搜索引擎，返回结果非常干净
    """
    if not tavily_key:
        st.error("❌ 未检测到 Tavily API Key")
        return None

    try:
        # 初始化客户端
        tavily = TavilyClient(api_key=tavily_key)
        
        # 执行搜索 (Tavily 的 search 方法非常强大)
        response = tavily.search(
            query=query,
            search_depth="advanced", # 深度搜索
            topic="news",            # 专注于新闻
            days=1,                  # 只看最近 24 小时
            max_results=7            # 获取 7 条高质量结果
        )
        
        results = response.get("results", [])
        if not results:
            return None

        # 格式化上下文给 Gemini
        context_text = ""
        for idx, item in enumerate(results):
            context_text += f"--- Source {idx+1} ---\nTitle: {item.get('title')}\nContent: {item.get('content')}\nURL: {item.get('url')}\n"
        
        return context_text

    except Exception as e:
        st.error(f"❌ Tavily 搜索接口报错: {e}")
        return None

# --- 3. Gemini 处理逻辑 (核心分析) ---
def process_news_with_gemini(google_key, raw_data, model_name):
    """
    调用 Google Gemini 进行深度分析
    """
    if not google_key:
        st.error("❌ 未检测到 Google API Key")
        return None

    try:
        genai.configure(api_key=google_key)
        
        # 配置：强制 JSON 输出，保证格式稳定
        generation_config = {
            "temperature": 0.4,
            "response_mime_type": "application/json", 
        }
        
        # 自动降级策略：如果选的新模型名字不对，自动回退到稳定版
        try:
            model = genai.GenerativeModel(model_name, generation_config=generation_config)
        except:
            model = genai.GenerativeModel("gemini-2.0-flash-exp", generation_config=generation_config)

        # Prompt: 专业的 AI 行业分析师角色
        system_prompt = """
        You are a Senior AI Analyst. 
        Analyze the provided search results and generate a structured Daily Briefing in Simplified Chinese (简体中文).

        Strict JSON Output format:
        {
            "breaking_news": [
                {"title": "Chinese Title", "summary": "Detailed summary in Chinese", "url": "Source URL", "source_name": "Source Name"}
            ],
            "business_trends": [
                {"trend": "Name of the trend", "analysis": "Business/Investment analysis in Chinese"}
            ],
            "new_tools": [
                {"name": "Tool Name (English)", "function": "Core function description in Chinese", "target_user": "Who should use this?"}
            ]
        }
        """
        
        user_input = f"Here is the raw news data from Tavily:\n{raw_data}"
        
        response = model.generate_content(system_prompt + "\n\n" + user_input)
        return response.text

    except Exception as e:
        st.error(f"❌ Gemini 推理报错: {e}")
        return None

# --- 4. 主界面逻辑 ---
def main():
    # 侧边栏：配置中心
    with st.sidebar:
        st.header("⚙️ API 配置中心")
        
        st.markdown("### 1. Google Gemini")
        google_api_key = st.text_input("Google API Key", type="password", placeholder="AIza...", key="google_key")
        
        st.markdown("### 2. Tavily Search")
        tavily_api_key = st.text_input("Tavily API Key", type="password", placeholder="tvly-...", key="tavily_key")
        st.caption("没有 Key? 去 [tavily.com](https://tavily.com/) 免费领一个")

        st.divider()
        
        model_choice = st.selectbox(
            "选择推理模型", 
            ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
            index=0
        )
        
        run_btn = st.button("🚀 开始生成日报", use_container_width=True)

    # 主区域
    st.title("⚡ AI 每日情报站 (Tavily 增强版)")
    st.markdown(f"**日期**: {datetime.date.today().strftime('%Y年%m月%d日')} | **数据源**: Tavily (AI Search)")
    
    if run_btn:
        if not google_api_key or not tavily_api_key:
            st.warning("⚠️ 请先在左侧填入两个 API Key")
            return

        # 状态 1: 搜索
        with st.status("📡 正在连接 Tavily 网络...", expanded=True) as status:
            status.write("🔍 正在深度检索全球 AI 资讯 (Last 24h)...")
            
            # 搜索词策略
            query = "Artificial Intelligence news latest 24 hours new AI model release startup funding"
            raw_news = search_with_tavily(tavily_api_key, query)
            
            if not raw_news:
                status.update(label="❌ 搜索失败 (检查 Key 或 网络)", state="error")
                return
            
            status.write("✅ 已获取高质量清洗数据")
            
            # 状态 2: 分析
            status.write(f"🧠 正在上传至 {model_choice} 进行语义分析...")
            json_result = process_news_with_gemini(google_api_key, raw_news, model_choice)
            
            if not json_result:
                status.update(label="❌ 报告生成中断", state="error")
                return
                
            status.update(label="✅ 情报构建完成！", state="complete", expanded=False)

        # 结果展示
        try:
            data = json.loads(json_result)
            
            # 板块 1: 核心新闻
            st.subheader("🚨 全球核心动态")
            for news in data.get("breaking_news", []):
                with st.expander(f"📰 {news['title']}", expanded=True):
                    st.markdown(f"**摘要**: {news['summary']}")
                    if 'source_name' in news:
                        st.caption(f"来源: {news['source_name']}")
                    st.markdown(f"[🔗 点击阅读原文]({news['url']})")
            
            st.divider()
            
            # 板块 2 & 3: 并列布局
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💰 商业风向")
                for item in data.get("business_trends", []):
                    st.info(f"**{item['trend']}**\n\n{item['analysis']}")
            
            with col2:
                st.subheader("🛠️ 新工具/模型")
                for tool in data.get("new_tools", []):
                    with st.container(border=True):
                        st.markdown(f"**🚀 {tool['name']}**")
                        st.markdown(f"功能: {tool['function']}")
                        st.caption(f"适用: {tool['target_user']}")

        except json.JSONDecodeError:
            st.error("数据解析异常，模型可能未返回标准 JSON。")
            with st.expander("查看原始返回"):
                st.code(json_result)

if __name__ == "__main__":
    main()
