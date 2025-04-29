import os
import json
import requests
from time import sleep
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DISCOURSE_COOKIE = ''

def set_discourse_cookie(cookie: str):
    global DISCOURSE_COOKIE
    DISCOURSE_COOKIE = '_t=' + cookie

def requ(topic_id, start_page=1, delay=0.2):
    """
    抓取指定话题的评论并返回评论列表
    """
    headers = {
        'Cookie': DISCOURSE_COOKIE,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    }
    
    all_posts = []
    page = start_page
    
    while True:
        url = f'https://shuiyuan.sjtu.edu.cn/t/{topic_id}.json?page={page}'
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=10)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"请求失败: {str(e)}")

        posts = data.get('post_stream', {}).get('posts', [])
        if not posts:
            break
            
        # 过滤首贴
        comments = [
            p.get('cooked', '') 
            for p in posts 
            if p.get('post_number', 0) > 1
        ]
        all_posts.extend(comments)
        page += 1
        sleep(delay)
    
    if not all_posts:
        return []
    
    return all_posts