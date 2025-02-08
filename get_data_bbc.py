import json
import uuid

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 "
                  "Safari/537.36",
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.7',
    'Connection': 'keep-alive',
}

API_KEY = "sk-4b502312e7d64ea28dc28e3de2ca4935"

# TODO 这里需根据当前数据集最后的id手动修改
doc_id = 0


# 获得新闻页面内部具体的url
def get_url(origin_url):
    response = requests.get(origin_url, headers=headers)
    # 如果Content-Type中有charset信息，则直接使用；否则，默认为utf-8
    content_type = response.headers.get('Content-Type', '')
    charset = 'utf-8'
    if 'charset=' in content_type:
        charset = content_type.split('charset=')[-1]
    if response.status_code == 200:
        # 使用正确的编码解析内容
        soup = BeautifulSoup(response.content.decode(charset), 'html.parser')
        url_content = soup.find("div", attrs={"data-testid": "alaska-grid"})
        div_list = url_content.find_all("div")
        for div in div_list:
            a = div.find('a')
            if a:
                link = a.get("href")
                # 分割获得前缀
                pre_url = "https://" + origin_url.split("/")[2]
                # 调用函数获得实际页面
                get_content(pre_url + link)
        return None
    return None


# 获得新闻内容---BBC
def get_content(url):
    global doc_id
    response = requests.get(url, headers=headers)

    # 如果Content-Type中有charset信息，则直接使用；否则，默认为utf-8
    content_type = response.headers.get('Content-Type', '')
    charset = 'utf-8'
    if 'charset=' in content_type:
        charset = content_type.split('charset=')[-1]

    if response.status_code == 200:
        # 使用正确的编码解析内容
        soup = BeautifulSoup(response.content.decode(charset), 'html.parser')
        article_content = soup.find("article")
        if article_content:
            article_content_list = article_content.find_all('div', attrs={"data-component": "text-block"})
            if article_content_list:
                text_content = ""
                for div in article_content_list:
                    text_content += div.get_text() + "\n"
                # print("----------------新的一篇报道-----------------")
                # print(text_content)

                qa_pairs = generate_qa(text_content.strip())  # 获得一个qa字典列表

                parts = url.split("/")
                if len(parts) > 1:
                    pre = parts[3]
                else:
                    pre = ""

                print(qa_pairs)

                if qa_pairs:
                    for qa in qa_pairs:
                        question = qa["question"]
                        answer = qa["answer"]
                        news_item = {
                            # "id": str(uuid.uuid4()),  # 生成唯一标识符
                            "id": doc_id,
                            "question": question,
                            "answer": answer,
                            "doc": text_content.strip()  # 去除末尾换行符
                        }

                        # 将内容写入文件
                        file_path = f"./data_en/{pre}.json".format(pre)
                        with open(file_path, 'a', encoding='utf-8') as f:
                            json.dump(news_item, f, ensure_ascii=False)
                            f.write('\n')  # 每个记录之后换行
                        print(f"已写入记录：{news_item['id']}")
                    doc_id += 1
                    return "success!"
                else:
                    print("生成的答案和问题为空")
                    return None
            else:
                print("未找到正文")
                return None
        else:
            print("未找到")
            return None
    else:
        print(f"请求失败，状态码为{response.status_code}")
        return None


# 调用模型api获得问题和答案
def generate_qa(doc):
    try:
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        example = {
            "question": "what is the capital of France？", "answer": "Paris"
        }

        completion = client.chat.completions.create(
            model="qwen-plus",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user',
                 'content': f'Based on the above material, please generate three questions with answers. It is '
                            f'required that the answers to the questions are all found in the above material and that '
                            f'they are objective questions. The material is as follows:\n{doc} \n Remember, '
                            f'the format of your answers is strictly as shown below:\n{example} '
                 }
            ]
        )

        generation = completion.choices[0].message.content
        print(generation)

        # 解析模型的回答为问答对
        qa_pairs = []
        for line in generation.strip().split('\n'):
            if 'question' in line and 'answer' in line:
                question = line.split(f"'question': '")[1].split(f"', 'answer': ")[0]
                answer = line.split(f"'answer': '")[1].rstrip("'")
                qa_pairs.append({'question': question, 'answer': answer})

        return qa_pairs or []

    except Exception as e:
        print(f"错误信息：{e}")
        # print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
        return []



def page_request(url):
    response = requests.get(url)
    if response.status_code == 200:
        # 使用正确的编码解析内容
        data = response.json()
        paths = [item['path'] for item in data['data']]

        for path in paths:
            get_content("https://www.bbc.com" + path)
            print("-------------一个页面已经爬取成功-----------------")
    else:
        print("请求失败")
    return None



if __name__ == "__main__":
    # 目录页面
    # url_list = [
    #     "https://www.bbc.com/travel"
    # ]

    url_list = []
    for page in range(0, 11, 1):
        # url = f"https://web-cdn.api.bbci.co.uk/xd/content-collection/98529df5-2749-4618-844f-96431b3084d9?country=sg&page={page}&size=9"
        # url = f"https://web-cdn.api.bbci.co.uk/xd/content-collection/6d50eb9d-ee20-40fe-8e0f-f506d6a02b78?country=ca&page={page}&size=9"
        url = f"https://web-cdn.api.bbci.co.uk/xd/content-collection/3da03ce0-ee41-4427-a5d9-1294491e0448?country=ca&page={page}&size=9"
        url_list.append(url)

    # 根据不同页面去构建数据集
    for origin_url in url_list:
        page_request(origin_url)

# 答案的括号去除，然后长的答案进行删除