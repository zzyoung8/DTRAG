import faiss
import jieba
import nltk
from nltk import word_tokenize
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import json

# 1. 初始化 sentence-transformer 模型
model = SentenceTransformer('./paraphrase-multilingual-MiniLM-L12-v2')

# 确保 NLTK 的数据已下载（仅需执行一次）
nltk.download('punkt')


def bm25(question, docs, language='zh'):
    """
    使用BM25算法实现文本相似度检索，支持中文和英文。

    参数:
    question: 需要检索的问题
    docs: 文档列表
    language: 语言 ('zh' 表示中文，'en' 表示英文)
    """
    if language == 'zh':
        # 对问题进行中文分词
        tokenized_query = list(jieba.cut(question))

        # 对文档进行中文分词
        tokenized_docs = [list(jieba.cut(doc)) for doc in docs]
    elif language == 'en':
        # 对问题进行英文分词
        tokenized_query = word_tokenize(question)

        # 对文档进行英文分词
        tokenized_docs = [word_tokenize(doc) for doc in docs]
        print(f"文档分词完成，共有 {len(tokenized_docs)} 个文档")
    else:
        raise ValueError("Unsupported language. Use 'zh' for Chinese or 'en' for English.")

    # 创建BM25模型
    bm25 = BM25Okapi(tokenized_docs)

    # 计算相似度得分并排序
    doc_scores = bm25.get_scores(tokenized_query)
    sorted_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)

    # 选择前N个最相关的文档
    top_n = 15
    n = min(top_n, len(docs))

    selected_docs = [docs[i] for i in sorted_indices[:n]]

    return selected_docs


# 3. 将文档分块
# def chunk_text(doc, max_tokens=60):
#     """文档分块"""
#     sentences = doc.split('。')  # 假设以句号为分隔符
#     chunks = []
#     current_chunk = ""
#
#     for sentence in sentences:
#         if len(current_chunk) + len(sentence) <= max_tokens:
#             current_chunk += sentence + "。"
#         else:
#             if current_chunk:
#                 chunks.append(current_chunk.strip())
#             current_chunk = sentence + "。"
#
#     if current_chunk:
#         chunks.append(current_chunk.strip())
#
#     return chunks


# 转换为向量并进行相似度搜索

def vector_retrieval(query, chunks):
    if not chunks:
        print("文档为空，无法进行检索")
        return None

    # 转换为向量
    chunk_embeddings = model.encode(chunks)
    query_embedding = model.encode([query])

    if chunk_embeddings.size == 0:
        print("无法为文本块生成向量")
        return None

    # 使用 FAISS 构建索引并进行相似度搜索
    dimension = chunk_embeddings.shape[1]  # 向量的维度
    index = faiss.IndexFlatL2(dimension)  # L2 距离的索引
    index.add(chunk_embeddings)  # 将所有文本块向量添加到索引中

    # 动态确定检索数量，最后k个
    total_chunks = len(chunks)
    top_k = 5
    k = min(total_chunks, top_k)

    # 检索相似的文本块并输出
    distances, indices = index.search(query_embedding, k)

    top_chunks = [chunks[i] for i in indices[0]]

    relevant_chunks = []
    threshold = 0.04
    for i, (chunk, distance) in enumerate(zip(top_chunks, distances[0])):
        similarity = 1 / (1 + distance)  # 将距离转换为相似度分数
        truncated_chunk = chunk[:20] + '...' if len(chunk) > 20 else chunk
        print(f"\n文本块 {i + 1}:")
        print(truncated_chunk)
        print(f"相似度分数: {similarity:.4f}")
        if similarity >= threshold:  # 设个阈值
            relevant_chunks.append(chunk)
    if not relevant_chunks:
        print("没有找到相关度足够高的文本块。")
        return None
    else:
        print(f"\n共找到 {len(relevant_chunks)} 个相关度较高的文本块。")
        return relevant_chunks


def main():
    data_path = 'data_en/en.json'
    # 1.爬虫数据集，获得问题
    updated_data = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()  # 去除空白行
            if not line:  # 如果行是空的，跳过
                print("警告：跳过空行。")
                continue
            try:
                data = json.loads(line)  # 尝试解析 JSON 行
            except json.JSONDecodeError:
                print(f"警告：无法解析行 '{line}'，跳过该行。")
                continue

            query = data['question']
            query_id = data['id']
            doc = data['doc']
            # 2.谷歌搜索api获得的网页内容
            doc_path = f'Document/en/query_{query_id}'
            try:
                with open(doc_path, 'r', encoding='utf-8') as fp:
                    document = json.load(fp)
                    if not document:
                        print(f"警告：文档 '{doc_path}' 为空。")
                        continue
                    # 这里先用BM25算法，再用向量密集检索
                    selected_docs = bm25(query, document, 'en')
                    new_content = vector_retrieval(query, selected_docs)
                    if new_content:
                        new_content.append(doc)
                        data['doc'] = new_content
                    updated_data.append(data)
            except FileNotFoundError:
                print(f"错误：找不到文件 '{doc_path}'。")
            except json.JSONDecodeError:
                print(f"错误：无法解析文件 '{doc_path}' 中的 JSON 数据。")

    # 将更新后的数据写回文件
    with open(data_path, 'w', encoding='utf-8') as f:
        for data in updated_data:
            json.dump(data, f, ensure_ascii=False)
            f.write('\n')
    print(f"\n文件已更新：{data_path}")


if __name__ == "__main__":
    main()
