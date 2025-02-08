import os.path
import re
import logging
import requests
import json
from bs4 import BeautifulSoup

# 下载必要的nltk数据
# nltk.download('punkt', quiet=True)
# nltk.download('stopwords', quiet=True)
# nltk.download('punkt_tab')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 '
                  'Safari/537.36 '
}

URL = 'https://customsearch.googleapis.com/customsearch/v1'
SEARCH_ID = '51ec18c8b6abe4406'
KEY = 'AIzaSyAigZJaTbWlIXbyG3ixmY3773GzyEYpz-I'
OUTPUT_DIR = 'Document/test'

if not os.path.exists(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_webpage_text(url):
    """获得google搜索后的网页文本内容"""
    try:
        webpage_response = requests.get(url, timeout=10)
        webpage_response.raise_for_status()  # 确保请求成功

        # 自动检测编码
        webpage_response.encoding = webpage_response.apparent_encoding

        soup = BeautifulSoup(webpage_response.text, 'html.parser')

        # 移除脚本、样式、导航等无关元素
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()

        # 获取所有段落文本
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])

        # 清理文本
        clean_text = re.sub(r'\s+', ' ', text).strip()
        return clean_text
    except Exception as e:
        logging.error(f"获取网页文本失败: {url} - {e}")
        return None


def split_text_into_paragraphs(text, target_length=350):
    """将文本分割成大约300-400字符的段落，确保每个段落以完整句子结束"""
    sentences = re.findall(r'[^!?。！？\.\!\?]+[!?。！？\.\!\?]', text)
    paragraphs = []
    current_paragraph = ""
    
    for sentence in sentences:
        if len(current_paragraph) + len(sentence) <= target_length:
            current_paragraph += sentence
        else:
            if current_paragraph:
                paragraphs.append(current_paragraph.strip())
            current_paragraph = sentence
    
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())
    
    return paragraphs


def google_search_api(question, query_id):
    params = {
        'cx': SEARCH_ID,
        'q': question,
        'key': KEY
    }

    response = requests.get(URL, headers=headers, params=params, timeout=10)

    if response.status_code == 200:
        results = response.json()
        print(results)
        print('-------------------------------------')
        print("搜索结果：")
        all_paragraphs = []
        for item in results.get('items', []):
            print(f"标题: {item['title']}")
            print(f"链接: {item['link']}")

            link_text = get_webpage_text(item['link'])

            if link_text is not None:
                paragraphs = split_text_into_paragraphs(link_text)
                all_paragraphs.extend(paragraphs)
                print(f'获取到 {len(paragraphs)} 个段落')
            else:
                print("无法获得文本")
            print("\n")

        # 写入文件 一个问题写一个文件
        # output_file = os.path.join(OUTPUT_DIR, sanitize_filename(f'{question.replace(" ", "_")}'))
        output_file = os.path.join(OUTPUT_DIR, f"query_{query_id}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_paragraphs, f, ensure_ascii=False, indent=2)
        
        print(f"已将 {len(all_paragraphs)} 个段落保存到文件: {output_file}")
    else:
        logging.error(f"请求失败，状态码: {response.status_code}")


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def main():
    # 所有问题
    file_path = 'data_en/temp.json'
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            question = data['question']
            query_id = data["id"]
            google_search_api(question, query_id)

    # 单个问题测试
    # QUESTION = '《青花》是谁的音乐作品？'
    # google_search_api(QUESTION)


if __name__ == '__main__':
    main()

