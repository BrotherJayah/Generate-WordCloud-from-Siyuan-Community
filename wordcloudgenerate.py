# wordcloudgenerate.py

import re
import os
import jieba
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import random
import colorsys
from collections import Counter
from wordcloud import WordCloud
import json
import markdown
from bs4 import BeautifulSoup
import cv2

DEFAULT_STOPWORDS = set()

def load_stopwords(stopword_path=None):
    """
    加载停用词集合：
    - 如果提供路径，从文件读取（每行一个词）。
    - 否则使用默认列表。
    """
    stopwords = set(DEFAULT_STOPWORDS)
    if stopword_path and os.path.exists(stopword_path):
        with open(stopword_path, 'r', encoding='utf-8') as f:
            for line in f:
                w = line.strip()
                if w:
                    stopwords.add(w)
    return stopwords

def markdown_to_plain_text(markdown_text):
    """Markdown 转纯文本（容错）"""
    try:
        html = markdown.markdown(str(markdown_text))
        return ''.join(BeautifulSoup(html, "html.parser").stripped_strings)
    except:
        return str(markdown_text)

def create_hsv_color_func():
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        h = random.random()
        s = 0.5 + random.random() * 0.5
        v = 0.5 + random.random() * 0.5
        return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
    return color_func

def preprocess_mask(mask_path):
    """稳健地读取并二值化掩模"""
    try:
        img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("无法读取掩模")
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    except Exception as e:
        print(f"掩模处理失败: {e}")
        return None

def wc(identifier, path='word.json', output_dir='.', mask_path=None, stopword_path=None):
    """
    生成词云并输出关键词频率排序。

    - path: 存放评论 JSON 列表的文件。
    - stopword_path: 可选的用户自定义停用词文件，每行一个词。

    返回:
      output_path (str): 词云图像路径
      sorted_keywords (List[Tuple[str,int]]): 按频率降序排列的词频列表
    """
    # 加载停用词
    stopwords = load_stopwords(stopword_path)

    # 读取文本列表
    with open(path, 'r', encoding='utf-8') as f:
        comments = json.load(f)

    # 提取纯文本并分词
    text = ''.join(BeautifulSoup(md, 'html.parser').get_text() for md in comments)
    seg_list = jieba.lcut(text)
    # 只保留中文、字母、数字，并过滤停用词和单字符无意义项
    filtered = [w for w in seg_list if re.match(r"[\u4e00-\u9fa5A-Za-z0-9]+$", w)
                and w not in stopwords and len(w) > 1]

    # 词频统计
    word_freq = Counter(filtered)
    # 过滤低频
    min_frequency = 1
    word_freq = {k: v for k, v in word_freq.items() if v >= min_frequency}
    print(f"有效词汇统计（出现≥{min_frequency}次，已去停用词）：{len(word_freq)} 个词")

    # 排序关键词
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    # 保存排序结果
    os.makedirs(output_dir, exist_ok=True)
    freq_path = os.path.join(output_dir, f"{identifier}_freq.json")
    with open(freq_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_keywords, f, ensure_ascii=False, indent=2)
    print(f"已保存关键词频率排序: {freq_path}")

    # 准备词云参数
    mask = preprocess_mask(mask_path) if mask_path else None
    font_path = os.path.join(os.path.dirname(__file__), 'font.ttf')
    if not os.path.exists(font_path):
        raise RuntimeError(f\"字体文件不存在，请检查 {font_path}\")
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=400,
        mask=mask,
        background_color='white',
        max_words=200,
        min_font_size=1,
        max_font_size=50,
        color_func=create_hsv_color_func(),
        collocations=False,
        scale=3,
        prefer_horizontal=0.9
    ).generate_from_frequencies(dict(sorted_keywords))

    # 可视化输出
    plt.figure(figsize=(8, 4), facecolor='white', dpi=300)
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')

    output_path = os.path.join(output_dir, f"{identifier}.png")
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.05, dpi=300)
    plt.close()

    print(f"词云已保存至: {output_path}")
    return output_path, sorted_keywords

# =============================== 新增形状处理函数 ===============================
def get_mask_shape(mask_array):
    """将numpy数组转换为轮廓描述（用于简单形状匹配）"""
    if mask_array is None:
        return 'circle'
    
    # 检测是否为矩形
    height, width = mask_array.shape
    if np.all(mask_array == 255):
        return 'rect'
    
    # 检测是否为圆形（近似判断）
    center_x, center_y = width//2, height//2
    y, x = np.ogrid[:height, :width]
    mask_circle = (x - center_x)**2 + (y - center_y)**2 <= (min(center_x, center_y))**2
    if np.array_equal(mask_array, mask_circle.astype(np.uint8)*255):
        return 'circle'
    
    return 'diamond'  # 其他情况使用默认形状
