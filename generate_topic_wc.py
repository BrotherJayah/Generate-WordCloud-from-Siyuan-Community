import os
import shutil
import webbrowser
import topic_requester 
import wordcloudgenerate

projroute = '.'
topic_id = ''  # 替换为目标帖子ID
mask_path = '.'

# 创建专用目录
output_dir = f'{projroute}/topic_{topic_id}'
os.makedirs(output_dir, exist_ok=True)

# 清屏函数
#os.system('cls' if os.name == 'nt' else 'clear')

# 生成或加载数据
data_path = f'{output_dir}/topic_{topic_id}_words.json'
if not os.path.exists(data_path):
    # 获取数据
    topic_requester.requ(topic_id)
    
    # 移动文件
    try:
        shutil.move(f'topic_{topic_id}_words.json', data_path)
    except FileNotFoundError as e:
        print(f"移动失败: {e}")

# 生成词云
wordcloudgenerate.wc(
    identifier=f'topic_{topic_id}',  # 修改标识符
    path=data_path,
    mask_path=mask_path,
    stopword_path='baidu_stopwords.txt',
    output_dir=output_dir
)

# 打开结果
webbrowser.open(f'{output_dir}/topic_{topic_id}.png')
