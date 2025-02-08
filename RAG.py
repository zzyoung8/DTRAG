import argparse
import json
import os.path
import re
import string
from collections import Counter

import dateparser
import spacy
import tqdm
import yaml
from sentence_transformers import SentenceTransformer, util
from models import *
from datetime import date

API_KEY = "sk-xx"

# 获取今天的日期
today = date.today()

# 如果你想以特定的格式输出日期，例如 YYYY-MM-DD
today = today.strftime("%Y-%m-%d")

nlp = spacy.load("zh_core_web_sm")


def detect_time(question):
    doc = nlp(question)
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME"]:
            return True
    parser_time = dateparser.parse(question, languages=['zh'])
    return parser_time is not None


def reflect(question, lan):
    # 预定义的标签
    if lan == 'zh':
        labels = ['运动', '足球', '电影', '文化', '科技', '教育', '旅行', '人物']
    else:
        labels = ['sports', 'soccer', 'movie', 'culture', 'technology', 'education', 'travel', 'future']

    # 加载预训练的句子嵌入模型
    model = SentenceTransformer('./paraphrase-multilingual-MiniLM-L12-v2')

    # 计算标签和输入问题的嵌入
    label_embeddings = model.encode(labels, convert_to_tensor=True)
    question_embedding = model.encode(question, convert_to_tensor=True)

    # 计算问题和每个标签的相似度
    similarities = util.cos_sim(question_embedding, label_embeddings)

    # 找到相似度最高的标签
    best_match_index = similarities.argmax()
    best_label = labels[best_match_index]

    return best_label


def format_instruction(query, docs, label, prompt, method):
    """
    根据不同的method格式化提示词
    """
    if method == 'zzy':
        if detect_time(query):
            return prompt['instruction_zzy_time_label'].format(QUERY=query, DOCS=docs, LABEL=label, TODAY=today)
        else:
            return prompt['instruction_zzy_label'].format(QUERY=query, DOCS=docs, LABEL=label)
    elif method == 'TA_ARE':
        return prompt['instruction_TA_ARE'].format(QUERY=query, DOCS=docs, EXAMPLE=prompt['example'], TODAY=today)
    elif method == 'UNRAG':
        return prompt['instruction_UNRAG'].format(QUERY=query)
    elif method == 'ablation_time':
        return prompt['instruction_zzy_label'].format(QUERY=query, DOCS=docs, LABEL=label)
    elif method == 'ablation_label':
        return prompt['instruction_zzy_time'].format(QUERY=query, DOCS=docs, TODAY=today)
    else:
        return prompt['instruction'].format(QUERY=query, DOCS=docs)


def predict(query, docs, answer, model, temperature, method, dataset):
    """
    生成步骤：将检索的文档和问题结合，生成最终的答案
    """
    # 将docs列表转换为字符串
    docs = '\n'.join(docs)

    # 加载提示词
    prompt = yaml.load(open('instruction.yaml', 'r'), Loader=yaml.FullLoader)[dataset]

    # 获取语言和日期
    lan = dataset[:2]

    # 获取标签
    label = reflect(query, lan) if method in ['zzy', 'ablation_time'] else None

    # 格式化提示词
    instruction_text = format_instruction(query, docs, label, prompt, method)

    # 生成预测
    prediction = model.generate(instruction_text, temperature)

    # 检查预测是否包含正确答案
    true = any(ans in prediction for ans in answer)

    return prediction, true


def metrics(result, metrics_file):
    f1_list = []
    precision_list = []
    recall_list = []
    match_total, accuracy_total = 0, 0

    for item in result:
        prediction = item['prediction']
        ground_truth = item['answer']

        # 准确度
        accuracy_total += 1 if correct(prediction, ground_truth) == 1 else 0

        # 匹配度
        match_total += 1 if match(prediction, ground_truth) == 1 else 0

        # 计算精确率、召回率、F1 分数
        precision, recall, f1 = precision_recall_f1(prediction, ground_truth)
        precision_list.append(precision)
        recall_list.append(recall)
        f1_list.append(f1)

    accuracy = accuracy_total / len(result)
    print("accuracy:", accuracy)
    match_avg = match_total / len(result)

    f1_avg = sum(f1_list) / len(f1_list)
    precision_avg = sum(precision_list) / len(precision_list)
    recall_avg = sum(recall_list) / len(recall_list)

    metric_template = {
        "accuracy": accuracy,
        "match_avg_score": match_avg,
        "precision_avg_score": precision_avg,
        "recall_avg_score": recall_avg,
        "f1_avg_score": f1_avg,
        "accuracy_total": accuracy_total,
        "match_total": match_total
    }
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(metric_template, f, ensure_ascii=False)


def precision_recall_f1(prediction, ground_truths):
    """计算 Precision, Recall 和 F1 分数"""
    prediction_tokens = normalize_answer(prediction).split()
    best_precision, best_recall, best_f1 = 0, 0, 0

    for ground_truth in ground_truths:
        ground_truth_tokens = normalize_answer(ground_truth).split()
        common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
        num_same = sum(common.values())

        if num_same == 0:
            precision, recall, f1 = 0, 0, 0
        else:
            precision = 1.0 * num_same / len(prediction_tokens)
            recall = 1.0 * num_same / len(ground_truth_tokens)
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # 保存最好的匹配
        if f1 > best_f1:
            best_precision, best_recall, best_f1 = precision, recall, f1

    return best_precision, best_recall, best_f1


def match(prediction, ground_truth):
    """答案中的黄金答案是否在预测中,可能后续加上标准化"""
    match_score = 1 if ground_truth[0] in prediction else 0
    return match_score


def correct(prediction, ground_truth):
    """指标的计算以及持久化存储; 预测的时候设置一个标签，表示是否中了，仅仅为正确率"""
    for ans in ground_truth:
        accuracy = 1 if ans in prediction else 0
    return accuracy


def normalize_answer(s):
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    # 中文的分词处理
    def chinese_tokenize(text):
        doc = nlp(text)
        return [token.text for token in doc]

    # 处理英文文本
    if re.search('[a-zA-Z]', s):
        return white_space_fix(remove_articles(remove_punc(lower(s))))
    else:
        # 如果是中文，先进行分词再处理
        tokens = chinese_tokenize(s)
        return ''.join(tokens)  # 返回分词后的结果


def f1_score(prediction, ground_truths):
    prediction_tokens = normalize_answer(prediction).split()
    f1_list = []
    for ground_truth in ground_truths:
        ground_truth_tokens = normalize_answer(ground_truth).split()
        common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
        num_same = sum(common.values())
        if num_same == 0:
            return 0
        else:
            precision = 1.0 * num_same / len(prediction_tokens)
            recall = 1.0 * num_same / len(ground_truth_tokens)
            f1 = (2 * precision * recall) / (precision + recall)
        f1_list.append(f1)
    return max(f1_list)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='zh_google', choices=['zh', 'zh_google', 'en'], help='dataset')
    parser.add_argument('--modelname', type=str, default='Qwen2.5',
                        choices=['Qwen1.5', 'Qwen2.5', 'chatglm', 'Llama', 'deepseek'],
                        help='model name')
    parser.add_argument('--api_key', type=str, default=API_KEY, help='API key if need')
    parser.add_argument('--url', type=str, default='https://api.openai.com/v1/completions', help='url of chatgpt')
    parser.add_argument('--plm', type=str, default='./model/Qwen2.5-7B-Instruct',
                        choices=["./model/Qwen1.5-7B-Chat", "./model/Qwen2.5-7B-Instruct", "./model/chatglm3-6b",
                                 "./model/llama-3-8B-Instruct", "./model/deepseek-7b-chat"],
                        help='local model path or model from huggingface')
    parser.add_argument('--method', type=str, default='TA_ARE', help='which method to run')
    parser.add_argument('--temperature', type=float, default=0.2, help='generation temperature')
    args = parser.parse_args()

    # 数据集
    dataset_path = f'data/{args.dataset}.json'
    instances = []  # 包含着所有python对象，dict的列表

    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            instances.append(json.loads(line))

    # 大模型
    modelname = args.modelname
    if modelname == 'chatgpt':
        model = OpenAIAPIModel(api_key=args.api_key, url=args.url)
    elif 'Llama' in modelname:
        model = LLama2(plm=args.plm)
    elif 'chatglm' in modelname:
        model = ChatglmModel(plm=args.plm)
    elif 'vicuna' in modelname:
        model = Vicuna(plm=args.plm)
    elif 'Qwen1.5' in modelname:
        model = Qwen(plm=args.plm)
    elif 'Qwen2.5' in modelname:
        model = Qwen2(plm=args.plm)
    elif 'deepseek' in modelname:
        model = Deepseek(plm=args.plm)
    elif 'Baichuan' in modelname:
        model = Baichuan(plm=args.plm)
    elif 'WizardLM' in modelname:
        model = WizardLM(plm=args.plm)
    elif 'BELLE' in modelname:
        model = BELLE(plm=args.plm)
    elif 'moss' in modelname:
        model = Moss(plm=args.plm)
    else:
        model = Qwen(plm=args.plm)

    # 结果路径
    result_path = f'results/{args.dataset}'
    if not os.path.exists(result_path):
        os.mkdir(result_path)

    result = []
    output_file = f'{result_path}/{args.modelname}_{args.method}_prediction.json'
    metrics_file = f'{result_path}/{args.modelname}_{args.method}_metrics.json'

    # 预测并写回
    with open(output_file, 'w', encoding='utf-8') as f:
        for instance in tqdm.tqdm(instances):
            question = instance['question']
            answer = instance['answer']
            docs = instance['doc']

            # 预测
            prediction, true = predict(question, docs, answer, model, args.temperature, args.method,
                                       args.dataset)

            template = {
                'id': instance['id'],
                'question': question,
                'answer': answer,
                'prediction': prediction,
                'true': true
            }

            result.append(template)
            f.write(json.dumps(template, ensure_ascii=False) + '\n')

    print(f"Result saved to {output_file}")

    # 各种指标
    metrics(result, metrics_file)


if __name__ == "__main__":
    main()
