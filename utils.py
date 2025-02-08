import json

import requests

from get_data import generate_qa


# transformers = 4.41.2

# 1. 一些学习例子
# 这里的文件是一堆json对象，所以每一行进行一次loads
# file_path = "./data/sports_google.json"
# with open(file_path, 'r', encoding='utf-8') as f:
#     count = 0
#     for line in f:
#         news_item = json.loads(line)   # 反序列化为python对象，此处不是文件流了，所以是loads不是load
#         # doc = news_item["content"]
#         count += 1
#     print(count)


# # 这里是load，并且文件是一个list
# with open(file_path, 'r', encoding='utf-8') as f:
#     qa_fairs = json.load(f)           # 从文件流中读取json格式的字符串，反序列化为一个Python对象
#     # print(type(qa_fairs))           # ---list
#     for qa in qa_fairs:               # qa为字典
#         print(qa["question"])

# 2. 基本函数
# 打开文件
def open_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return lines


# 写入文件
def write_file(file_path, res):
    with open(file_path, 'w', encoding="utf-8") as f:
        for data in res:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")


# TODO 3. 由于大模型生成的答案可能包含着""和''的问题，可能后续需要处理；处理答案后有'}的问题
# file_path = 'data_en/news.json'
# with open(file_path, 'r', encoding='utf-8') as f:
#     result = []
#     for line in f:
#         data = json.loads(line)
#         answer = data['answer']
#         if answer[-2:] == "'}":
#             data['answer'] = answer[:-2]
#         result.append(data)
#
# write_file(file_path, result)
# print(f"\n文件已更新")

# 3.分为积极消极文档
# 测试
# with open('data/sports_v2.json', 'r', encoding='utf-8') as f:
#     data = f.readline()
#     data_dict = json.loads(data)
#     answer = data_dict['answer']
#     positive, negative = [], []
#     for item in data_dict['doc']:
#         if answer in item:
#             positive.append(item)
#         else:
#             negative.append(item)
#
#     print(positive)
#     print(len(positive))


# 实操分为积极消极文档
# update_data = []
# path = "data/sports_google.json"
# with open(path, 'r', encoding='utf-8') as f:
#     datas = f.readlines()
#     for data in datas:
#         data_dict = json.loads(data)
#         answer = data_dict['answer']
#         positive, negative = [], []
#         for item in data_dict['doc']:
#             if answer in item:
#                 positive.append(item)
#             else:
#                 negative.append(item)
#
#         data_dict['positive'] = positive
#         data_dict['negative'] = negative
#         del data_dict['doc']
#
#         update_data.append(data_dict)
#
# with open(path, 'w', encoding='utf-8') as fp:
#     for entry in update_data:
#         json.dump(entry, fp, ensure_ascii=False)
#         fp.write('\n')
#
# print("数据成功处理并写回")


# 4.混合数据集
# import os
# import random
#
# path = 'data_mix'
# if not os.path.exists(path):
#     os.mkdir(path)
#
# def get_label(path):
#     return path.split('/')[1].split('.')[0]
#
# def read_file(path):
#     result = []
#     label = path.split('/')[1].split('.')[0]
#     with open(path, 'r', encoding='utf-8') as f:
#         lines = f.readlines()
#         for line in lines:
#             data = json.loads(line)
#             data['label'] = label
#             result.append(data)
#     return result
#
#
# def write_file(path, data):
#     with open(path, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False)
#         f.write('\n')
#
# data1path = 'data/sports_google.json'
# data2path = 'data/zh.json'
# label1 = get_label(data1path)
# label2 = get_label(data2path)
#
# data1 = read_file(data1path)
# data2 = read_file(data2path)
#
# data = data1 + data2
# random.shuffle(data)
#
# mixDataPath = path + f'/{label1}_{label2}.json'
# write_file(mixDataPath, data)

# 5.计算准确率
correct_num = 0
with open('./Qwen2.5_test_prediction.json', 'r', encoding='utf-8') as f:
    result = f.readlines()
    for item in result:
        data = json.loads(item)
        if data['true'] == 1:
            correct_num += 1
    correct_rate = correct_num / len(result)
print(
    correct_num
)
print(f"correct_rate: {correct_rate}")


# 6.answer转为list写回
# deleted_res = []
# file_path = "data_en/en_ori.json"
# with open(file_path, 'r', encoding='utf-8') as f:
#     lines = f.readlines()
#     for line in lines:
#         data = json.loads(line)
#         answer = []
#         answer.append(data['answer'])
#         data['answer'] = answer
#         deleted_res.append(data)
#
# write_file(file_path, deleted_res)


# 7.将删减后的数据集写回数据集中
# 读取并处理原始数据文件
# doc_str = []
# with open('./data/sports_google.json', 'r', encoding='utf-8') as f:
#     lines = f.readlines()
#     for index, line in enumerate(lines):
#         try:
#             data = json.loads(line.strip())  # 使用 strip() 去除首尾空白字符
#             template = {
#                 "question": data["question"],
#                 "doc": data["doc"]
#             }
#             doc_str.append(template)
#         except json.JSONDecodeError as e:
#             print(f"Error decoding JSON at line {index + 1}: {e}")
#             print(f"Problematic line content: {line}")
#
# # 读取并处理已处理的数据文件
# data_list = []
# with open('./sports_process_save.json', 'r', encoding='utf-8') as f:
#     lines = f.readlines()
#     for index, line in enumerate(lines):
#         try:
#             data = json.loads(line.strip())  # 使用 strip() 去除首尾空白字符
#             del data['prediction']
#             del data['label']
#             for doc in doc_str:
#                 if data["question"] == doc['question']:
#                     data['doc'] = doc['doc']
#             data_list.append(data)
#         except json.JSONDecodeError as e:
#             print(f"Error decoding JSON at line {index + 1}: {e}")
#             print(f"Problematic line content: {line}")
#
# # 将处理后的数据写回文件
# with open('./data/sports_google.json', 'w', encoding='utf-8') as f:
#     for data in data_list:
#         json.dump(data, f, ensure_ascii=False)
#         f.write('\n')


# 8. 应该是把id放前面
# res = []
# file_path = "data_en/en_ori.json"
# with open(file_path, 'r', encoding='utf-8') as f:
#     for line in f.readlines():
#         data = json.loads(line)
#         # 先将 id 放在前面，重建字典
#         if "doc_id" in data:
#             new_data = {'id': data['doc_id']}
#             del data['doc_id']
#         else:
#             new_data = {'id': data['id']}
#         # del data['doc_id']
#         # 合并剩余的键值对
#         new_data.update(data)
#         res.append(new_data)
#
#
# def assign_number(res):
#     for i, data in enumerate(res):
#         data["id"] = i
#     return res
#
#
# res = assign_number(res)
# write_file(file_path, res)
#
# # 将修改后的内容写回文件
# with open('data/zh.json', 'w', encoding='utf-8') as f:
#     for data in res:
#         json.dump(data, f, ensure_ascii=False)
#         f.write('\n')


# 9. 找到google前后数据集中的错误进行分析
# def find_error():
#     res = []
#     file_path1 = "Qwen2.5_ori_prediction.json"
#     file_path2 = "Qwen2.5_google_prediction.json"
#     lines1 = open_file(file_path1)
#     lines2 = open_file(file_path2)
#     for line1, line2 in zip(lines1, lines2):
#         data1 = json.loads(line1.strip())
#         data2 = json.loads(line2.strip())
#         if data1['true'] == 1 and data2['true'] == 0:
#             res.append(data1)
#             res.append(data2)
#     write_file("compare.json", res)
#
# find_error()


# 留着，当做未来思路吧
# example = {
#     "sports": [
#         "Question: 2023年U20男足世界杯的东道主是哪个国家？\n Answer: 阿根廷",
#         "Question: 梅西在2021美洲杯足球赛中获得了哪两个奖项？\n Answer: 金球奖和金靴奖",
#     ],
#     "e": [
#         "Question: What is the"
#     ],
#     "geography": [
#         "Question: What is the capital of Germany?\nAnswer: [No].",
#         "Question: How many countries are in Africa?\nAnswer: [Yes].",
#     ],
#     "general": [
#         "Question: What is the boiling point of water?\nAnswer: [No].",
#         "Question: Who won the last World Cup?\nAnswer: [Yes].",
#     ]
# }
