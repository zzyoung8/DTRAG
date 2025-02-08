import json
import os
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

# 具体新闻页面的前缀
# sports_pre_url = "https://sports.gmw.cn/"
# e_pre_url = "https://e.gmw.cn/"

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
        url_content = soup.find("div", attrs={"class": "channelLeftPart"})
        # url_content = soup.find("div", attrs={"class": "right_content"})
        ul_list = url_content.find_all("ul", class_="channel-newsGroup")
        for ul in ul_list:
            li_list = ul.find_all("li")
            if li_list:
                for li in li_list:
                    a = li.find('a')
                    link = a.get("href")
                    # 分割获得前缀
                    pre_url = "https://" + origin_url.split("/")[2] + "/"
                    # 调用函数获得实际页面
                    get_content(pre_url + link)
        return None
    return None


# 获得新闻内容---光明网
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
        article_content = soup.find("div", attrs={"class": "u-mainText"})

        if article_content:
            text_content = ""
            for p in article_content.find_all("p"):
                text_content += p.get_text() + "\n"

            qa_pairs = generate_qa(text_content.strip())  # 获得一个qa字典列表

            parts = url.split("//")
            if len(parts) > 1:
                part1 = parts[1]
                pre = part1.split(".")[0]
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
                    file_path = f"./data/{pre}.json".format(pre)
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
        print(f"请求失败，状态码为{response.status_code}")
        return None


# 调用模型api获得问题和答案
def generate_qa(doc):
    # doc = (
    #     "新华社马德里9月23日电（谢宇智）赛季伊始，西甲豪门巴塞罗那便遭遇迎头一棒。"
    #     "门将特尔施特根23日因膝伤接受手术，赛季基本报销。特尔施特根在22日巴萨客场对阵比利亚雷亚尔的比赛中因伤离场。"
    #     "赛后巴萨门将被确诊右膝髌腱完全断裂。巴萨俱乐部23日发布官方公告，确认特尔施特根已在俱乐部医疗团队的监督下于巴塞罗那医院成功接受手术。"
    #     "尽管巴萨没有给出特尔施特根的具体恢复时间，但据西班牙多家媒体预测，这名德国球员将缺阵7至8个月之久。"
    #     "此前特尔施特根已在2020和2021年因为同一部位的伤势两次接受手术。"
    #     "特尔施特根的意外受伤也打乱了巴萨主帅汉斯·弗利克的部署。目前队中仍有伊尼亚基·佩尼亚和阿斯特拉拉加两名门将可用。"
    #     "但西班牙媒体认为，巴萨倾向于寻找一名新的门将来暂时替代特尔施特根，只是目前尚不确定俱乐部是打算直接引入一名没有在任何球队注册的门将，还是等到冬季转会市场重开再进行引援。"
    # )

    try:
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        example = {
            "question": "鲁迅原名是什么？", "answer": "周树人",
            "question": "《青花》是谁的音乐作品？", "answer": "周传雄"
        }

        completion = client.chat.completions.create(
            model="qwen-plus",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user',
                 'content': f'根据以上材料，请生成2个问题与答案。要求问题的答案均在以上材料中可以找到，且均为客观问题。材料如下：\n{doc}。\n 记住，你回答的格式严格如下所示:\n{example}'}
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

        # 将问题和答案对保存为 JSON 文件
        # response_path = "./qa_response.json"
        # with open(response_path, 'w', encoding='utf-8') as f:
        #     json.dump(qa_pairs, f, ensure_ascii=False, indent=4)
        #
        # print(f"问题与答案已保存到 {response_path}")

        return qa_pairs or []

    except Exception as e:
        print(f"错误信息：{e}")
        # print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
        return []


if __name__ == "__main__":
    # 目录页面
    url_list = [
                # "https://sports.gmw.cn/node_9638.htm",  # 运动足球
                # "https://sports.gmw.cn/node_9638_2.htm",
                # "https://e.gmw.cn/node_8758.htm",  # 明星
                # "https://e.gmw.cn/node_8758_2.htm",
                # "https://e.gmw.cn/node_8756.htm",  # 电影
                # "https://e.gmw.cn/node_8756_2.htm",
                # "https://e.gmw.cn/node_8756_3.htm",
                # "https://e.gmw.cn/node_8756_4.htm",
                # "https://e.gmw.cn/node_8756_5.htm",
                # "https://e.gmw.cn/node_8756_6.htm",
                # "https://tech.gmw.cn/node_10601.htm",    # 科技 人工智能
                "https://edu.gmw.cn/node_9757.htm"
                ]

    url_list_temp = [""]

    # 根据不同页面去构建数据集
    for origin_url in url_list:
        get_url(origin_url)

    # generate_qa()
    # 数据集 凑成需要的样子 跑代码 然后说这个数据集的特点，原始的提示词的问题以及后续prompt解决该问题 RGB的数据集更简单，看那个代码吧
