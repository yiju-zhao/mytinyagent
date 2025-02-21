from dataclasses import dataclass
from datetime import datetime
from string import Template

# 数据库配置
DB_USER="postgres"
DB_PASSWORD="nasa718"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="test_db"

DATABASE_URL=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 会议信息 NeurIPS 2024
START_DATE=datetime(2024, 12, 10)
END_DATE=datetime(2024, 12, 15)
LOCATION="Vancouver, Canada"
WEBSITE="https://neurips.cc/virtual/2024/index.html"
CATEGORY="machine learning, neuroscience, statistics, optimization, computer vision, natural language processing, life sciences, natural sciences, social sciences"
DESCRIPTION="The Conference and Workshop on Neural Information Processing Systems is a machine learning and computational neuroscience conference held every December. Along with ICLR and ICML, it is one of the three primary conferences of high impact in machine learning and artificial intelligence research."

@dataclass
class MilvusConfig:
    host: str = "localhost"
    port: int = 19530
    collection_name: str = "paper_collection"
    dimension: int = 768  # Embedding dimension
    index_type: str = "IVF_FLAT"
    metric_type: str = "L2"

class PDFAnalyzerConfig:
    # 定义各个章节的标题, 用于提取章节内容.可以持续刷新
    SECTION_TITLES = {
            "abstract": {"abstract"},
            "introduction": {"introduction", "background", "preliminaries", "preliminary"},
            "keywords": {"keywords", "key words", "index terms", "indexing terms"},
            "related_work": {"related work", "prior work", "literature review", "related studies"},
            "methodology": {"methodology", "methods", "method", "approach", "proposed method", 
                            "model", "architecture", "framework", "algorithm", "system design"},
            "experiment": {"experiment", "experiments", "experimental setup", "experiment setup",
                        "setup", "implementation details", "evaluation", "evaluation setup"},
            "ablation":{"ablation","ablation study"},
            "results": {"results", "performance", "findings", "observations", "empirical results"},
            "discussion": {"discussion", "analysis", "interpretation"},
            "summary":{"summary"},
            "conclusion": {"conclusion", "final remarks", "closing remarks"},
            "limitations":{"limitations"},
            "acknowledgments": {"acknowledgments", "acknowledgements", "funding", "author contributions"},
            "references": {"references", "bibliography", "cited works"},
            "appendix": {"appendix", "supplementary material", "supplementary", "additional materials"}
        }
        # 论文拆分参数
    MAX_LINE_PER_CHUNK = 25  # 每个 chunk 最大行数
    OVERLAP_LINES = 5  # 上下文重叠行数
    REFERENCE_CHUNK_LINE_SIZE = 30  # 参考文献一个chunk的行数量
    REFERENCE_MAX_CHUNK_SIZE = 20 # 一篇文章的reference 假设有个最长，避免某些文章在reference 之后放了很长的不相干文字。以上两个数相乘
    REFERENCE_OVERLAP_LINES = 4  # 参考文献块重叠行数

     # 定义提示词模版
    AUTHOR_AFFILIATION_PROMPT_TEMPLATE = Template('''
        你将收到以下输入：
        1.	一段论文文本，其中包含作者姓名、机构和电子邮件等信息。
        2.	一个作者信息的 JSON 数组，其中部分字段缺失或有误。

        你的任务是根据论文文本直接生成更新后的作者 JSON 数组，具体要求如下：
        •	仅输出最终更新后的 JSON，其他内容（代码、解释、思考过程）一律不需要。
        •	保留 JSON 中已存在的有效 author_id，不要修改。
        •	清理作者姓名（去除多余符号、引号、括号），并补充 full_name。
        •	提取并填充 email 和 affiliation 字段。
        •	若作者姓名中带有 *，则 is_corresponding 为 true，否则为 false。
        •	如果 nationality 缺失，请根据机构、电子邮件域名或姓名推测填入。
        •	确保 contribution_order 按作者在论文中出现的顺序递增。

        输出格式要求：
        •	仅输出更新后的 JSON 数组（无引导语、无多余解释、无代码片段、无中间推理）。
        •	确保输出是有效的、可直接解析的 JSON。
        ---

        ### Input:
        Paper Text:
        $context

        Authors:
        $author_json

        ---

        ### Output:
        Return **only a raw JSON object**. **No explanations or extra text.**  
        Example output:
        ```json
        [
        {
            "name": "Ryan Greenblatt",
            "author_id": "~Ryan_Greenblatt1",
            "affiliation": ["Redwood Research"],
            "email": "ryan@rdwrs.com",
            "contribution_order": 0,
            "is_corresponding": true,
            "nationality": "United States"
        },
        {
            "name": "Fabien Roger",
            "author_id": "~Fabien_Roger1",
            "affiliation": ["Redwood Research"],
            "email": "fabien.d.roger@gmail.com",
            "contribution_order": 1,
            "is_corresponding": true,
            "nationality": "France"
        }
        ]                                                                                  
        ''')
    
    REFERENCES_PROMPT_TEMPLATE = Template('''
        You will be given several citation fragments from academic papers.  
        Your task is to extract key citation information **only if** the citation fragment appears to be a valid reference.  
        If the fragment is **not** a valid reference (e.g., a broken or incomplete reference, or unrelated information), **return an empty list**.

        Each valid citation should return a JSON object with the following fields:

        - "title": (string, required) The title of the cited paper.  
        - "author": (string) Authors separated by commas. Use "unknown" if not available.  
        - "year": (integer) Year of publication. Use null if unknown.  
        - "journal": (string) Journal or publication name. Use "unknown" if not available.  
        - "web_url": (string) URL to the original paper or web source. Use "unknown" if not available.  

        ### Input:
        $reference_chunk_text

        ### Important Notes:
        - **If the input does not appear to be a valid reference**, skip it and return an empty array.  
        - Extract as much accurate information as possible from valid references.  
        - Return **only a raw JSON array** of citation objects (or an empty array if invalid).  
        - **Do not include any explanations, comments, or extra text.**  
        - Ensure the JSON is well-formed and parsable.  
        - For unknown or missing information, use `"unknown"` or `null` where appropriate.  

        ### Example Output:
        ```json
        [
        {
            "title": "Program synthesis with large language models",
            "author": "Austin, J., Odena, A., Nye, M., Bosma, M., Michalewski, H., et al.",
            "year": 2021,
            "journal": "arXiv preprint arXiv:2108.07732",
            "web_url": "https://arxiv.org/abs/2108.07732"
        },
        {
            "title": "Cooperative Hardware-Prompt Learning for Snapshot Compressive Imaging",
            "author": "unknown",
            "year": null,
            "journal": "unknown",
            "web_url": "unknown"
        }
        ]
        ''')
    KEYWORDS_PROMPT_TEMPLATE = Template('''
        You are an expert academic assistant. Your task is to extract the most important keywords that represent the core ideas of the given research paper.

        You will be provided with:
        - The **abstract** of the paper (may be empty if not available).
        - The **conclusion** of the paper (may be empty if not available).
        - An optional **TL;DR summary** (if available) that provides a one-sentence summary of the paper.
        - A set of **initial keywords** from metadata (which may be empty or incomplete).

        Instructions:
        1. Carefully analyze the **abstract**, **conclusion** (if provided), and **TL;DR** (if provided) to understand the main topics, methods, and key findings.
        2. If the **conclusion** is missing, rely on the **abstract** and **TL;DR** to identify the core aspects of the paper.
        3. Use the **initial keywords** as a reference. You may:
        - Retain relevant keywords.
        - Modify or refine them if necessary.
        - Add new keywords based on the provided texts.
        4. Select keywords that best capture:
        - The main research problem and solution.
        - Key methods, models, or frameworks used or introduced.
        - Important application domains or use cases.
        - Novel contributions or unique technical terms.

        5. Guidelines for choosing keywords:
        - Use concise terms or short phrases (e.g., "transformer models", "graph neural networks", "multi-agent systems").
        - Avoid overly generic words (e.g., "study", "paper", "result") unless essential.
        - Exclude duplicates or semantically redundant keywords.
        - Provide **5 to 10 high-quality keywords** that best summarize the paper.

        Texts to analyze:
        TL;DR (if any):
        $tldr_text

        Initial keywords (if any):
        $initial_keywords

        Abstract (may be empty):
        $abstract_text

        Conclusion (may be empty):
        $conclusion_text

        Output requirements:
        - Return **only a JSON object** containing the final list of keywords.
        - **Do not** include explanations, comments, or extra information.
        - If you cannot find enough keywords, include as many valid ones as possible without guessing.

        Example output:
        {
        "keywords": [
            "large language models",
            "alignment techniques",
            "reinforcement learning from human feedback",
            "zero-shot generalization",
            "efficient model scaling"
        ]
        }
        ''')
