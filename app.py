import streamlit as st
from tavily import TavilyClient
import google.generativeai as genai
import json
import datetime

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="AI 每日情报站 (修复版)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 美化
st.markdown("""
    <style>
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 搜索逻辑 (Tavily 引擎) ---
def search_with_tavily(tavily_key, query):
    """
    使用 Tavily 搜索，这是专为 LLM 设计的搜索引擎
    """
    if not tavily_key:
        st.error("❌ 未检测到 Tavily API Key")
        return None

    try:
        # 初始化客户端
        tavily = TavilyClient(api_key=tavily_key)
        
        # 执行搜索
        response = tavily.search(
            query=query,
            search_depth="basic",    # 改为 basic 以节省时间，稳定为主
            topic="news",            
            days=1,                  
            max_results=5            
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
        
        # 配置：强制 JSON 输出
        # 注意：只有 1.5 及以上版本才完美支持 response_mime_type
        # 如果是旧版 gemini-pro，我们需要在 prompt 里更强硬地要求 JSON
        generation_config = {
            "temperature": 0.4,
        }
        
        # 如果是 1.5 系列，开启原生 JSON 模式
        if "1.5" in model_name:
            generation_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(model_name, generation_config=generation_config)

        # Prompt: 专业的 AI 行业分析师角色
        system_prompt = """
        You are a Senior AI Analyst. 
        Analyze the provided search results and generate a structured Daily Briefing in Simplified Chinese (简体中文).

        CRITICAL: Output MUST be valid JSON code. No Markdown code blocks (like ```json). Just the raw JSON string.

        JSON Structure:
        {
            "breaking_news": [
                {"title": "Chinese Title", "summary": "Detailed summary in Chinese", "url": "Source URL", "source_name": "Source Name"}
            ],
            "business_trends": [
                {"trend": "Name of the trend", "analysis": "Business analysis in Chinese"}
            ],
            "new_tools": [
                {"name": "Tool Name (English)", "function": "Function description in Chinese", "target_user": "Target User"}
            ]
        }
        """
        
        user_input = f"Here is the raw news data from Tavily:\n{raw_data}"
        
        response = model.generate_content(system_prompt + "\n\n" + user_input)
        return response.text

    except Exception as e:
        # 捕获具体的 404 或 429 错误并显示给人话
        error_msg = str(e)
        if "404" in error_msg:
            st.error(f"❌ 模型找不到 (404): {model_name}。请尝试在左侧切换为 'gemini-pro'。")
        elif "429" in error_msg:
            st.error("❌ 配额超限 (429): Google 暂时限制了你的免费调用。请稍后重试或切换模型。")
        else:
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

        st.divider()
        
        st.markdown("### 3. 模型选择 (关键)")
        # 这里使用了更稳健的模型名称列表
        model_choice = st.selectbox(
            "选择推理模型", 
            [
                "gemini-1.5-flash-latest", # 推荐：最新稳定版 Flash
                "gemini-1.5-pro-latest",   # 推荐：最新稳定版 Pro
                "gemini-pro",              # 保底：1.0版 (绝对可用)
                "gemini-1.5-flash"         # 旧写法 (备用)
            ],
            index=0,
            help="如果报错 404，请选择 'gemini-pro' 试试"
        )
        
        run_btn = st.button("🚀 开始生成日报", use_container_width=True)

    # 主区域
    st.title("🛡️ AI 每日情报站 (Tavily + 修复版)")
    st.markdown(f"**日期**: {datetime.date.today().strftime('%Y年%m月%d日')} | **数据源**: Tavily API")
    
    if run_btn:
        if not google_api_key or not tavily_api_key:
            st.warning("⚠️ 请先在左侧填入两个 API Key")
            return

        # 状态 1: 搜索
        with st.status("📡 正在连接 Tavily 网络...", expanded=True) as status:
            status.write("🔍 正在检索全球 AI 资讯 (Last 24h)...")
            
            # 搜索词
            query = "Artificial Intelligence news latest 24 hours new AI model release startup funding"
            raw_news = search_with_tavily(tavily_api_key, query)
            
            if not raw_news:
                status.update(label="❌ 搜索失败 (检查 Key 或 网络)", state="error")
                return
            
            status.write("✅ 已获取数据")
            
            # 状态 2: 分析
            status.write(f"🧠 正在调用 {model_choice} 进行分析...")
            json_result = process_news_with_gemini(google_api_key, raw_news, model_choice)
            
            if not json_result:
                status.update(label="❌ 报告生成中断", state="error")
                return
                
            status.update(label="✅ 情报构建完成！", state="complete", expanded=False)

        # 结果展示
        try:
            # 清洗可能存在的 Markdown 标记 (容错处理)
            cleaned_json = json_result.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_json)
            
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
            st.error("数据解析异常。建议切换 'gemini-1.5-flash-latest' 模型重试。")
            with st.expander("查看原始返回"):
                st.text(json_result)

if __name__ == "__main__":
    main()
