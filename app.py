import streamlit as st
from tavily import TavilyClient
import google.generativeai as genai
import json
import datetime
import time

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="AI 每日情报站 (Pro Max)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：优化大量文本的阅读体验
st.markdown("""
    <style>
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .report-text {
        font-family: "Source Sans Pro", sans-serif;
        line-height: 1.6;
    }
    /* 优化 Expander 的样式 */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1.05rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 增强型搜索逻辑 (多路召回) ---
def search_aggregated_data(tavily_key):
    """
    执行多路搜索策略：
    1. 通用新闻 (News)
    2. GitHub/开源 (Code)
    3. 商业/创投 (Business)
    """
    if not tavily_key:
        st.error("❌ 请输入 Tavily API Key")
        return None

    client = TavilyClient(api_key=tavily_key)
    all_results = []
    
    # 定义搜索任务列表
    tasks = [
        {
            "category": "Breaking News",
            "query": "Artificial Intelligence breaking news latest 24 hours major announcements",
            "limit": 20  #以此确保能筛选出15条
        },
        {
            "category": "GitHub & Tools",
            "query": "latest AI open source projects GitHub trending release new AI tools framework",
            "limit": 15
        },
        {
            "category": "Business & Market",
            "query": "AI startup funding news acquisition market analysis report latest",
            "limit": 15
        }
    ]

    status_text = ""
    for task in tasks:
        try:
            # 使用 advanced 模式获取更高质量的全文片段
            response = client.search(
                query=task['query'],
                search_depth="advanced", 
                topic="news",
                days=1,
                max_results=task['limit']
            )
            
            items = response.get("results", [])
            for item in items:
                # 给原始数据打上标签，方便 LLM 分类
                all_results.append(f"[{task['category']}] Title: {item.get('title')}\nContent: {item.get('content')}\nURL: {item.get('url')}\nSource: {item.get('url')}\n")
            
            time.sleep(0.5) # 稍微防抖，避免触发 QPS 限制
            
        except Exception as e:
            st.warning(f"⚠️ 子任务 {task['category']} 搜索部分失败: {e}")
            continue

    return "\n".join(all_results)

# --- 3. Gemini 3.0 深度分析逻辑 ---
def process_news_with_gemini(google_key, raw_data, model_name):
    if not google_key:
        st.error("❌ 请输入 Google API Key")
        return None

    try:
        genai.configure(api_key=google_key)
        
        # 配置：开大 Output Token 上限，因为这次内容很多
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json",
            "max_output_tokens": 8192 # 确保长文不截断
        }

        model = genai.GenerativeModel(model_name, generation_config=generation_config)

        # 超级详细的 System Prompt
        system_prompt = """
        You are an elite Chief AI Intelligence Officer (CAIO).
        Your task is to generate a comprehensive "Daily AI Deep Dive Report" in Simplified Chinese (简体中文).

        Input Data: Mixed raw search results (Breaking News, GitHub, Business).

        **CRITICAL QUANTITY REQUIREMENTS:**
        1.  **Breaking News (核心头条): Exactly 15 items.** 2.  **Market Insights (市场洞察): Exactly 10 items.**
        3.  **New Tech Stack (新技术/GitHub): Exactly 10 items.**

        **CONTENT QUALITY REQUIREMENTS:**
        -   **Deep Summaries:** Do NOT just translate the title. You must analyze the content and extract 2-3 core bullet points (key takeaways) for EACH item.
        -   **GitHub Integration:** Specifically look for GitHub links or open-source releases in the data and put them in "New Tech Stack".
        -   **Professional Tone:** Use tech-savvy and investor-grade language.

        **JSON OUTPUT STRUCTURE:**
        {
            "breaking_news": [
                {
                    "title": "Chinese Title", 
                    "core_points": ["Point 1", "Point 2"], 
                    "url": "Source URL", 
                    "source": "Source Name (e.g. GitHub/TechCrunch)"
                }
            ],
            "market_analysis": [
                {
                    "topic": "Trend Topic", 
                    "insight": "Deep analysis of the business impact (50-80 words)",
                    "url": "Related URL"
                }
            ],
            "new_tech": [
                {
                    "name": "Tool/Repo Name", 
                    "desc": "Function description", 
                    "tech_highlight": "Why is it technically interesting?",
                    "url": "GitHub/Demo URL"
                }
            ]
        }
        """
        
        # 调用模型
        response = model.generate_content(system_prompt + "\n\nRAW DATA POOL:\n" + raw_data)
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            st.error("❌ Google API 限流 (429)。请稍等几分钟再试，或检查您的 API 额度。")
        else:
            st.error(f"❌ Gemini 推理错误: {e}")
        return None

# --- 4. 主程序 ---
def main():
    with st.sidebar:
        st.header("⚙️ 2026 情报控制台")
        
        google_api_key = st.text_input("Google API Key", type="password", key="g_key")
        tavily_api_key = st.text_input("Tavily API Key", type="password", key="t_key")
        
        st.divider()
        
        # 模型选择
        model_choice = st.selectbox(
            "AI 核心引擎", 
            [
                "gemini-2.0-flash-exp",   # 推荐：处理长文本能力极强且快
                "gemini-1.5-pro-latest",  # 备选：逻辑最强，但可能稍慢
                "gemini-1.5-flash-latest" # 备选：最快
            ],
            index=0,
            help="建议使用 Pro 或 2.0 Flash 以处理大量数据"
        )
        
        st.info("📊 模式: 深度聚合 (15+10+10)")
        run_btn = st.button("🚀 生成全量日报", use_container_width=True)

    st.title("🌌 AI 每日情报站 (Deep Dive)")
    st.caption(f"📅 {datetime.date.today()} | 🔍 多路召回: News + GitHub + Capital")

    if run_btn:
        if not google_api_key or not tavily_api_key:
            st.warning("⚠️ 请先完善 API Key")
            return

        # 1. 多路搜索阶段
        with st.status("🕵️‍♂️ 正在执行全网深度检索...", expanded=True) as status:
            status.write("📡 正在连接 Tavily (News Channel)...")
            status.write("🐙 正在扫描 GitHub Trending & Releases...")
            status.write("💰 正在分析 Venture Capital 动态...")
            
            raw_data = search_aggregated_data(tavily_api_key)
            
            if not raw_data:
                status.update(label="❌ 搜索全线失败，请检查网络/Key", state="error")
                return
            
            status.write(f"✅ 已聚合 {len(raw_data)} 字符的原始情报，准备分析...")
            
            # 2. LLM 分析阶段
            status.write(f"🧠 {model_choice} 正在阅读并提炼核心观点 (预计耗时 30秒)...")
            json_result = process_news_with_gemini(google_api_key, raw_data, model_choice)
            
            if not json_result:
                status.update(label="❌ 生成失败", state="error")
                return
                
            status.update(label="✅ 深度日报构建完成！", state="complete", expanded=False)

        # 3. 渲染展示
        try:
            data = json.loads(json_result)
            
            # --- Tab 布局管理大量内容 ---
            tab1, tab2, tab3 = st.tabs(["🚨 核心头条 (15)", "💰 市场洞察 (10)", "🛠️ 技术栈/GitHub (10)"])
            
            with tab1:
                st.subheader("🔥 今日必读")
                breaking = data.get("breaking_news", [])
                if not breaking: st.warning("暂无头条数据")
                
                for i, item in enumerate(breaking):
                    # 使用 Expander 保持页面整洁，展开看详情
                    with st.expander(f"{i+1}. {item['title']}", expanded=False):
                        st.markdown("**核心观点:**")
                        for point in item.get('core_points', []):
                            st.markdown(f"- {point}")
                        st.caption(f"来源: {item.get('source', 'Web')} | [🔗 原文链接]({item['url']})")

            with tab2:
                st.subheader("📈 商业与资本")
                market = data.get("market_analysis", [])
                cols = st.columns(2) # 双栏布局
                for i, item in enumerate(market):
                    col = cols[i % 2]
                    with col:
                        with st.container(border=True):
                            st.markdown(f"#### {item['topic']}")
                            st.info(item['insight'])
                            if item.get('url'):
                                st.markdown(f"[相关报道]({item['url']})")

            with tab3:
                st.subheader("💻 GitHub & New Tools")
                tools = data.get("new_tech", [])
                for item in tools:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"### 🚀 {item['name']}")
                            st.markdown(f"**功能**: {item['desc']}")
                            st.markdown(f"**技术亮点**: `{item.get('tech_highlight', 'N/A')}`")
                        with c2:
                            st.link_button("访问项目", item['url'])

        except Exception as e:
            st.error("❌ JSON 解析异常 (可能是内容过长导致格式截断)")
            st.expander("调试: 原始返回").code(json_result)

if __name__ == "__main__":
    main()
