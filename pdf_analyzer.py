import json
import os
import re
from markitdown import MarkItDown
from typing import List, Dict

class PDFAnalyzer:
    def __init__(self, pdf_path: str):
        """
        初始化 PDF 处理器
        
        :param pdf_path: PDF 文件路径
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件 {pdf_path} 不存在!")
        
        self.pdf_path = pdf_path
        self.text = self._extract_text()


    def _extract_text(self) -> str:
        """
        提取 PDF 中的纯文本

        :return: 提取的文本内容
        """
        md = MarkItDown()
        result = md.convert(self.pdf_path)
        return result.text_content
    
    def get_full_text(self) -> str:
        return self.text
    
    def _extract_text_before_abstract(self) -> str:
        # 使用正则表达式进行不区分大小写的匹配
        short_text = self.text[:2000]
        match = re.search(r"abstract", short_text, re.IGNORECASE)
        
        if match:
            abstract_position = match.start()  # 获取 "Abstract" 的位置
            extracted_text = short_text[:abstract_position].strip()
        else:
            # 如果没有找到 "Abstract"，直接返回前500个字符
            extracted_text = short_text[:500].strip()

        # 检查提取的文本长度是否小于10字符，我也怀疑是没有正确提取。假设：正常文章加作者应该大于10个
        if len(extracted_text) < 10:
            return short_text[:500].strip()

        return extracted_text

    def extract_authors(self, author_names) -> Dict:
        """
        从文本中提炼作者信息，默认作者信息在文本靠前部分。
        假设作者信息包含名字、邮箱、学校等信息
        author_names: 字符串，逗号分隔。已知的名字，可以作为输入，作为大模型推理的上下文
        :return: 返回提炼出的作者信息，以JSON格式返回
        """
        authors_info = []
        
        # 提取PDF的title 和abstraction 之前的文字
        author_context = self._extract_text_before_abstract()
        # 调用大模型来推理出名字
        # 假设从文本解析出的作者名
        author_names = ["John Doe", "Jane Smith"]
        authors_info = []
        for idx, name in enumerate(author_names):
            author_info = {
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@example.com",
                "affiliation": "AI Lab",
                "sequence": idx + 1,
                "is_corresponding": (idx == 0)  # 默认第一个是通讯作者
            }
            authors_info.append(author_info)
                
        return json.dumps(authors_info, ensure_ascii=False)

