import streamlit as st
# --- 页面配置 ---
st.set_page_config(page_title="Discourse 词云生成器", layout="centered")
st.title("水源社区交互式词云生成")

import json
from streamlit_echarts import st_echarts
import topic_requester
import wordcloudgenerate
import pandas as pd
import os
from PIL import Image
import hashlib

# --- 用户输入 (Sidebar) ---
st.sidebar.header("配置参数")

# Cookie 输入
default_cookie = os.getenv("DISCOURSE_COOKIE", "")
cookie_input = st.sidebar.text_area(
    "Discourse 登录 Cookie", value=default_cookie, height=100,
    help="在此粘贴你在 shuiyuan.sjtu.edu.cn 的登录 Cookie，可从浏览器开发者工具获取。"
)
if not cookie_input:
    st.sidebar.error("需要提供有效的 DISCOURSE_COOKIE 才能抓取评论")
    st.stop()
topic_requester.set_discourse_cookie(cookie_input)

# 多话题ID输入
topic_ids_input = st.text_input(
    "请输入话题ID（多个用逗号分隔）", 
    value="369211,254606,365091",
    help="可输入多个话题ID，用英文逗号分隔。例如：366971,367000,367123"
)
topic_ids = [tid.strip() for tid in topic_ids_input.split(',') if tid.strip()]
if not topic_ids:
    st.error("至少需要提供一个有效的话题ID")
    st.stop()

# 其他参数
mask_file = st.file_uploader("上传词云掩模图（可选 PNG/JPG）", type=["png","jpg","jpeg"])
stopword_file = st.file_uploader("上传停用词文件（可选 txt，每行一个词）", type=["txt"])

# 生成按钮
if st.button("生成词云"):
    all_comments = []
    total_count = 0
    error_ids = []
    
    # 遍历抓取所有话题
    for tid in topic_ids:
        with st.spinner(f"正在抓取话题 {tid} 的评论..."):
            try:
                # 获取评论数据（返回评论列表）
                comments = topic_requester.requ(tid)
                if not comments:
                    st.warning(f"话题 {tid} 未抓取到任何评论，已跳过")
                    error_ids.append(tid)
                    continue
                
                all_comments.extend(comments)
                total_count += len(comments)
                st.success(f"话题 {tid} 抓取成功，获得 {len(comments)} 条评论")
                
            except Exception as e:
                st.error(f"话题 {tid} 抓取失败: {str(e)}")
                error_ids.append(tid)
                continue
    
    # 验证有效数据
    valid_ids = [tid for tid in topic_ids if tid not in error_ids]
    if not valid_ids:
        st.error("所有话题均未抓取到有效评论")
        st.stop()
    
    # 保存合并数据
    combined_identifier = hashlib.md5('_'.join(sorted(valid_ids)).encode()).hexdigest()[:8]
    combined_path = f"combined_{combined_identifier}_words.json"
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    
    st.success(f"成功合并 {total_count} 条评论（来自 {len(valid_ids)} 个有效话题）")

    # 准备文件路径
    mask_path = None
    if mask_file:
        mask_path = f"mask_{combined_identifier}.png"
        with open(mask_path, 'wb') as f:
            f.write(mask_file.getbuffer())
    
    stopword_path = None
    if stopword_file:
        stopword_path = f"stopword_{combined_identifier}.txt"
        with open(stopword_path, 'wb') as f:
            f.write(stopword_file.getbuffer())

    # 生成词云与频次
    with st.spinner("生成词云并排序关键词…"):
        try:
            img_path, sorted_keywords = wordcloudgenerate.wc(
                identifier=f"combined_{combined_identifier}",
                path=combined_path,
                mask_path=mask_path,
                stopword_path=stopword_path,
                output_dir=".",
            )
        except Exception as e:
            st.error(f"词云生成失败: {str(e)}")
            st.stop()

    # 显示结果
    st.image(img_path, caption="生成的词云图", use_container_width=True)

    # 下载按钮
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    st.download_button(
        label="下载静态词云图 (PNG)",
        data=img_bytes,
        file_name=f"combined_{combined_identifier}.png",
        mime="image/png"
    )

    # 交互式词云
    data = [{"name": w, "value": freq} for w, freq in sorted_keywords]
    option = {
        "tooltip": {"show": True},
        "series": [{
            "type": 'wordCloud',
            "shape": 'circle',
            "gridSize": 8,
            "sizeRange": [12, 60],
            "rotationRange": [-90, 90],
            "textStyle": {"normal": {}},
            "emphasis": {"focus": 'self', "textStyle": {"shadowBlur": 10, "shadowColor": '#333'}},
            "data": data
        }]
    }
    st.subheader("互动词云（鼠标悬停查看频率并放大）")
    st_echarts(option, height=400)

    # 显示Top20
    top20 = sorted_keywords[:20]
    df = pd.DataFrame(top20, columns=["关键词", "频率"])
    df.index = df.index + 1
    df.index.name = "top"
    styled = df.style.set_properties(**{'text-align': 'center'})
    st.subheader("Top 20 高频关键词")
    st.dataframe(styled, use_container_width=True)

    # 清理临时文件
    temp_files = [combined_path]
    if mask_path and os.path.exists(mask_path):
        temp_files.append(mask_path)
    if stopword_path and os.path.exists(stopword_path):
        temp_files.append(stopword_path)
    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass