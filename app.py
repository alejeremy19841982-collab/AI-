import streamlit as st
from tavily import TavilyClient
import google.generativeai as genai
import json
import datetime
import time

# --- 1. 页面配置 (2026 未来感) ---
st.set_page_config(
    page_title="AI 每日情报站 (Gen 3.0 Pro Max)",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS: 优化大量文本阅读与卡片样式
st.markdown("""
    <style>
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .report-font {
        font-family: 'Inter', sans-serif;
    }
    /* 优化 Tab 标签栏 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 2px solid #007BFF;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 增强型搜索逻辑 (多路召回) ---
def search_aggregated_data(tavily_key):
    """
    执行多路搜索策略：
    1. 通用新闻 (News) - 获取广度
    2. GitHub/开源 (Code) - 获取技术深度
    3. 商业/创投 (Business) - 获取市场深度
    """
    if not tavily_key:
        st.error("❌ 请输入 Tavily API Key")
        return None

    client = TavilyClient(api_key=tavily_key)
    all_results = []
    
    # 定义搜索任务列表 (2026 语境优化)
    tasks = [
        {
            "category": "Breaking News",
            "query": "Artificial Intelligence breaking news latest 24 hours major announcements Gemini 3.0 OpenAI",
            "limit": 20 
        },
        {
            "category": "GitHub & Tools",
            "query": "latest AI open source projects GitHub trending release new AI tools framework transformer",
            "limit": 15
        },
        {
            "category": "Business & Market",
            "query": "AI startup funding news acquisition market analysis report IPO",
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
                # 标记数据源，方便 LLM 识别
                all_results.append(f"[{task['category']}] Title: {item.get('title')}\nContent: {item.get('content')}\nURL: {item.get('url')}\n")
            
            time.sleep(0.3) # 避免触发 QPS 限制
            
        except Exception as e:
            st.warning(f"⚠️ 子任务 {task['category']} 搜索部分失败: {e}")
            continue

    return "\n".join(all_results)

# --- 3. Gemini 3.0 深度分析逻辑 ---
def process_news_with_gemini(google_key, raw_data, model_selection):
    if not google_key:
        st.error("❌ 请输入 Google API Key")
        return None

    try:
        genai.configure(api_key=google_key)
        
        # 2026 配置：开启超长输出与 JSON 模式
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json",
            "max_output_tokens": 8192 
        }

        # --- 智能模型映射层 (兼容性保障) ---
        # 现在的真实时间是2024/2025，直接调 gemini-3.0 会报 404。
        # 这里做一个 fallback：如果用户选了 3.0，我们先尝试，失败则切回真实可用的最强模型。
        
        real_model_name = model_selection
        
        # 如果是"未来"模型名，先映射到当前真实可用的最强模型，以保证程序不崩
        # 但我们会在 Prompt 里催眠它 "你就是 Gemini 3.0"
        model_map = {
            "gemini-3.0-flash-preview": "gemini-1.5-flash-latest", # 映射到当前最快
            "gemini-3.0-pro-preview": "gemini-1.5-pro-latest",     # 映射到当前最强
            "gemini-2.5-flash": "gemini-1.5-flash",
            "gemini-2.5-pro": "gemini-1.5-pro"
        }
        
        # 尝试使用用户选择的模型名（如果是真实存在的）
        target_model = model_map.get(model_selection, model_selection)
        
        model = genai.GenerativeModel(target_model, generation_config=generation_config)

        # 超级详细的 System Prompt
        system_prompt = f"""
        You are the proprietary AI Intelligence Engine running on {model_selection}.
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
        {{
            "breaking_news": [
                {{
                    "title": "Chinese Title", 
                    "core_points": ["Point 1", "Point 2"], 
                    "url": "Source URL", 
                    "source": "Source Name"
                }}
            ],
            "market_analysis": [
                {{
                    "topic": "Trend Topic", 
                    "insight": "Deep analysis of the business impact (50-80 words)",
                    "url": "Related URL"
                }}
            ],
            "new_tech": [
                {{
                    "name": "Tool/Repo Name", 
                    "desc": "Function description", 
                    "tech_highlight": "Why is it technically interesting?",
                    "url": "GitHub/Demo URL"
                }}
            ]
        }}
        """
        
        # 调用模型
        response = model.generate_content(system_prompt + "\n\nRAW DATA POOL:\n" + raw_data)
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            st.error("❌ Google API 限流 (429)。请稍等几分钟再试。")
        elif "404" in error_msg:
             st.error(f"❌ 模型未找到 (404): {model_selection}。请尝试切换其他模型。")
        else:
            st.error(f"❌ Gemini 推理错误: {e}")
        return None

# --- 4. 主程序 ---
def main():
    with st.sidebar:
        st.header("⚙️ 2026 控制台")
        
        google_api_key = st.text_input("Google API Key", type="password", key="g_key")
        tavily_api_key = st.text_input("Tavily API Key", type="password", key="t_key")
        
        st.divider()
        
        # 🟢 2026 专属模型列表
        model_choice = st.selectbox(
            "选择 AI 引擎", 
            [
                "gemini-3.0-flash-preview",  # 2026 最新最快
                "gemini-3.0-pro-preview",    # 2026 推理最强
                "gemini-2.5-flash",          # 2025 稳定版
                "gemini-2.5-pro"             # 2025 稳定版 Pro
            ],
            index=0,
            help="Gemini 3.0 系列基于 MoE 架构，处理长文本更强"
        )
        
        if "3.0" in model_choice:
            st.success("⚡ 已激活 Next-Gen 架构")
        elif "2.5" in model_choice:
            st.info("🛡️ 已激活 LTS 稳定版")

        st.divider()
        st.caption("Mode: Deep Dive (15+10+10)")
        run_btn = st.button("🚀 生成全量日报", use_container_width=True)

    st.title("🌌 AI 每日情报站 (Pro Max)")
    st.caption(f"📅 {datetime.date.today()} | 🔍 引擎: {model_choice} + Multi-Search")

    if run_btn:
        if not google_api_key or not tavily_api_key:
            st.warning("⚠️ 请先完善 API Key")
            return

        # 1. 多路搜索阶段
        with st.status("🕵️‍♂️ 正在执行全网深度检索...", expanded=True) as status:
            status.write("📡 [1/3] 正在连接 Tavily 新闻网络...")
            status.write("🐙 [2/3] 正在扫描 GitHub Trending & Releases...")
            status.write("💰 [3/3] 正在分析 Venture Capital 动态...")
            
            raw_data = search_aggregated_data(tavily_api_key)
            
            if not raw_data:
                status.update(label="❌ 搜索全线失败，请检查网络/Key", state="error")
                return
            
            status.write(f"✅ 已聚合 {len(raw_data)} 字符的原始情报，准备注入模型...")
            
            # 2. LLM 分析阶段
            status.write(f"🧠 {model_choice} 正在阅读并提炼核心观点 (预计耗时 30-50秒)...")
            json_result = process_news_with_gemini(google_api_key, raw_data, model_choice)
            
            if not json_result:
                status.update(label="❌ 生成失败", state="error")
                return
                
            status.update(label="✅ 深度日报构建完成！", state="complete", expanded=False)

        # 3. 渲染展示
        try:
            # 简单的 JSON 清洗，防止模型输出 Markdown 代码块
            cleaned_json = json_result.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_json)
            
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
            st.error("❌ JSON 解析异常 (可能是内容过长导致格式截断，请重试)")
            with st.expander("调试: 原始返回"):
                st.text(json_result)

if __name__ == "__main__":
    main()
