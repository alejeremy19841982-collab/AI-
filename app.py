import streamlit as st
from tavily import TavilyClient
import google.generativeai as genai
import json
import datetime
import time

# --- 1. 页面配置 (2026 真实版) ---
st.set_page_config(
    page_title="AI 每日情报站 (Gemini 3.0 Real)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 美化
st.markdown("""
    <style>
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .report-font { font-family: 'Inter', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 多路搜索逻辑 (保持不变) ---
def search_aggregated_data(tavily_key):
    if not tavily_key:
        st.error("❌ 请输入 Tavily API Key")
        return None

    client = TavilyClient(api_key=tavily_key)
    all_results = []
    
    # 2026年的搜索关键词优化
    tasks = [
        {
            "category": "Breaking News",
            "query": "Artificial Intelligence breaking news latest 24 hours Gemini 3 Flash Deep Think updates",
            "limit": 20 
        },
        {
            "category": "GitHub & Tools",
            "query": "latest AI open source projects GitHub trending release new AI tools framework",
            "limit": 15
        },
        {
            "category": "Business & Market",
            "query": "AI startup funding news acquisition market analysis report 2026 Q1",
            "limit": 15
        }
    ]

    for task in tasks:
        try:
            response = client.search(
                query=task['query'],
                search_depth="advanced", 
                topic="news",
                days=1,
                max_results=task['limit']
            )
            for item in response.get("results", []):
                all_results.append(f"[{task['category']}] Title: {item.get('title')}\nContent: {item.get('content')}\nURL: {item.get('url')}\n")
            time.sleep(0.3)
        except Exception as e:
            st.warning(f"⚠️ {task['category']} 搜索失败: {e}")
            continue

    return "\n".join(all_results)

# --- 3. Gemini 3.0 真实调用逻辑 ---
def process_news_with_gemini(google_key, raw_data, model_name):
    if not google_key:
        st.error("❌ 请输入 Google API Key")
        return None

    try:
        genai.configure(api_key=google_key)
        
        # Gemini 3.0 原生支持 JSON Schema，无需 Prompt 强行约束
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json",
            "max_output_tokens": 8192 
        }

        model = genai.GenerativeModel(model_name, generation_config=generation_config)

        system_prompt = f"""
        You are an elite AI Analyst in January 2026.
        Generate a "Daily AI Deep Dive Report" in Simplified Chinese (简体中文).

        **Input Data:** Real-time search results (News, GitHub, Business).
        
        **Requirements:**
        1. **Breaking News:** Exactly 15 items. Focus on Gemini 3.0, GPT-5 rumors, and 2026 trends.
        2. **Market:** Exactly 10 items.
        3. **Tech:** Exactly 10 items.
        4. **Core Points:** Extract 2-3 bullet points per item.

        **JSON Output Structure:**
        {{
            "breaking_news": [
                {{"title": "CN Title", "core_points": ["p1", "p2"], "url": "URL", "source": "Source"}}
            ],
            "market_analysis": [
                {{"topic": "Trend", "insight": "Analysis", "url": "URL"}}
            ],
            "new_tech": [
                {{"name": "Tool Name", "desc": "Desc", "tech_highlight": "Highlight", "url": "URL"}}
            ]
        }}
        """
        
        response = model.generate_content(system_prompt + "\n\nDATA:\n" + raw_data)
        return response.text

    except Exception as e:
        st.error(f"❌ API 调用失败: {e}")
        # 2026年特有的 Deprecation 提示
        if "404" in str(e):
             st.warning("⚠️ 如果提示 404，请检查您是否还在尝试调用已停用的 Gemini 2.5 Preview 版本。请切换到 Gemini 3 Flash。")
        return None

# --- 4. 主程序 ---
def main():
    with st.sidebar:
        st.header("⚙️ 2026 控制台")
        google_api_key = st.text_input("Google API Key", type="password")
        tavily_api_key = st.text_input("Tavily API Key", type="password")
        
        st.divider()
        
        # 🟢 修正：使用真实的 2026 模型 ID (基于搜索结果)
        # 1.1 提到 "Gemini 3 Flash"
        # 3.4 提到 "gemini-3-pro-preview"
        # 2.1 提到 "Gemini 3 Deep Think"
        model_choice = st.selectbox(
            "选择 AI 引擎", 
            [
                "gemini-3-flash",          # 2025.12.17 发布，当前默认
                "gemini-3-pro-preview",    # 2025.11.18 发布
                "gemini-3-deep-think",     # 2025.12.03 发布 (深度推理)
                "gemini-2.5-flash"         # 2025.04.17 发布 (上一代稳定版)
            ],
            index=0
        )
        
        st.caption(f"当前时间: {datetime.date.today()}")
        
        if "deep-think" in model_choice:
            st.info("🧠 已激活深度推理模式 (MoE)")
        elif "flash" in model_choice:
            st.success("⚡ 已激活高速模式")

        run_btn = st.button("🚀 生成全量日报", use_container_width=True)

    st.title("🌌 AI 每日情报站 (2026 Live)")
    
    if run_btn:
        if not google_api_key or not tavily_api_key:
            st.warning("⚠️ 请完善 API Key")
            return

        with st.status("🕵️‍♂️ 正在执行全网检索 (2026 Q1)...", expanded=True) as status:
            status.write("📡 [1/3] 正在获取 Gemini 3.0 生态动态...")
            status.write("🐙 [2/3] 正在扫描 GitHub Trending...")
            status.write("💰 [3/3] 正在分析 2026 投融资市场...")
            
            raw_data = search_aggregated_data(tavily_api_key)
            
            if not raw_data:
                status.update(label="❌ 搜索失败", state="error")
                return
            
            status.write(f"✅ 已聚合数据，正在发送至 {model_choice}...")
            json_result = process_news_with_gemini(google_api_key, raw_data, model_choice)
            
            if not json_result:
                status.update(label="❌ 生成失败", state="error")
                return
                
            status.update(label="✅ 完成！", state="complete", expanded=False)

        try:
            cleaned_json = json_result.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_json)
            
            tab1, tab2, tab3 = st.tabs(["🚨 核心头条 (15)", "💰 市场洞察 (10)", "🛠️ 技术栈 (10)"])
            
            with tab1:
                st.subheader("🔥 2026 今日必读")
                for i, item in enumerate(data.get("breaking_news", [])):
                    with st.expander(f"{i+1}. {item['title']}", expanded=False):
                        st.markdown("**核心观点:**")
                        for point in item.get('core_points', []):
                            st.markdown(f"- {point}")
                        st.caption(f"来源: {item.get('source', 'Web')} | [🔗 原文链接]({item['url']})")

            with tab2:
                st.subheader("📈 2026 市场风向")
                for item in data.get("market_analysis", []):
                    st.info(f"**{item['topic']}**\n\n{item['insight']}")

            with tab3:
                st.subheader("💻 新工具 & GitHub")
                for item in data.get("new_tech", []):
                    with st.container(border=True):
                        st.markdown(f"**🚀 {item['name']}**")
                        st.markdown(f"{item['desc']}")
                        st.markdown(f"*亮点: {item.get('tech_highlight')}*")
                        if item.get('url'):
                            st.link_button("查看项目", item['url'])

        except Exception as e:
            st.error("❌ 数据解析异常")
            st.code(json_result)

if __name__ == "__main__":
    main()
