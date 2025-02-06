import json
import os
import re
from time import sleep
from markitdown import MarkItDown
from string import Template
from typing import List, Dict
from openai import OpenAI
from openai.types.beta.threads.message_create_params import (
    Attachment,
    AttachmentToolFileSearch,
)

class PDFAnalyzer:
    def __init__(self, pdf_path: str):
        # 初始化 PDF 处理器 param pdf_path: PDF 文件路径
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件 {pdf_path} 不存在!")
        
        self.pdf_path = pdf_path
        self.text = self._extract_text()
        self.references_text = self._extract_text_after_references()

        # 初始化 OpenAI API
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided either through constructor or OPENAI_API_KEY environment variable")
 
        self.openai_client = OpenAI(api_key=self.api_key)

        # 定义提示词模版
        self.AUTHOR_AFFILIATION_PROMPT_TEMPLATE = Template('''
        Given the text from an academic paper and a list of author names, extract affiliations following these steps:

        Step 1: First identify ALL institution affiliations in the text, looking for:
        - Superscript numbers/markers (¹,²,³ or *,+,#) next to author names
        - Institution names following these markers
        - Only extract high-level institutions (universities, research institutes, companies)
                                                           
        Step 2: Look for email addresses:
        - Check for email addresses marked with symbols like *, †, or explicitly stated
        - Look for email addresses in footnotes or contact information
        - Look for corresponding author indicators which often have email addresses                                                   

        Step 3: Match authors to their affiliations by:
        - Looking for superscript numbers/markers next to each author's name
        - Linking these markers to the corresponding institution affiliations
        - Some authors may have multiple affiliations marked by multiple superscripts
                                                            
        Text from paper:
        $context

        Author names: $author_names

        Return ONLY a raw JSON object with this exact structure:
        {
            "institutions": [
                {"id": "1", "name": "First Institution Name"},
                {"id": "2", "name": "Second Institution Name"}
            ],
            "author_affiliations": [
                {
                    "name": "Author Name",
                    "affiliation_ids": ["1", "2"],
                    "email": "author@institution.edu"  // null if not found
                }
            ]
        }

        Example response for "John Smith¹,²*, Jane Doe²":
        {
            "institutions": [
                {"id": "1", "name": "Stanford University"},
                {"id": "2", "name": "Google Research"}
            ],
            "author_affiliations": [
                {
                    "name": "John Smith",
                    "affiliation_ids": ["1", "2"],
                    "email": "john.smith@stanford.edu"
                },
                {
                    "name": "Jane Doe",
                    "affiliation_ids": ["2"],
                    "email": null
                }
            ]
        }                                                                                                      

        ''')
        self.REFERENCES_PROMPT_TEMPLATE = Template('''
        Given the following reference text from an academic paper, extract the key bibliographic information following these steps:
        Step 1: Identify the core citation elements:
        - Title of the paper/article
        - Authors (all authors listed)
        - Publication year
        - Journal/Conference name
        - URL/Web link (if available)

        Step 2: Format special cases:
        - For conference papers, use the conference name as journal
        - For preprints, include the repository (e.g., arXiv) in journal field
        - URLs can include arXiv links, DOI links, or direct web addresses

        Reference text:
        $context

        Return ONLY a raw JSON object with this exact structure:
        {
            "title": "Complete title of the paper",
            "authors": ["Author 1", "Author 2"],  // Array of author names
            "year": 2024,  // null if not found
            "journal": "Journal or Conference name",  // null if not found
            "web_url": "https://..."  // null if not found
        }

        Example responses:

        For a journal paper:
        {
            "title": "High-performance large-scale image recognition without normalization",
            "authors": ["Hugo Touvron", "Matthieu Cord", "Alexandre Sablayrolles"],
            "year": 2021,
            "journal": "Nature",
            "web_url": "https://www.nature.com/articles/s41586-021-03819-2"
        }

        For a preprint:
        {
            "title": "Language Models are Few-Shot Learners",
            "authors": ["Tom B. Brown", "Benjamin Mann"],
            "year": 2020,
            "journal": "arXiv",
            "web_url": "https://arxiv.org/abs/2005.14165"
        }

        Notes:
        - Extract complete titles, don't truncate
        - Include all authors in the order listed
        - For year, extract only the publication year (not submission/revision dates)
        - Journal names should be complete, not abbreviated
        - URLs should be complete and valid
        ''')

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
    
    def get_references_text(self) -> str:
        return self.references_text
    
    # 提取 abstract 之前的文字
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
    
    # 提取 conclusion 之后的文字
    def _extract_text_after_references(self) -> str:
        # 使用正则表达式进行分大小写的匹配
        full_text = self.text
        match = re.search(r"References", full_text)
        
        if match:
            references_position = match.end() # 获取 "References" 的位置
            extracted_text = full_text[references_position:references_position+15000].strip()
        else:
            # 如果没有找到 "References"，直接返回后500个字符
            return None
        
        return extracted_text

    # 调用 LLM
    def _call_llm(self, prompt: str) -> str:
        """
        调用OpenAI的大模型来处理给定的提示并提取作者信息
    
        :param prompt: 给定的提示文本
        :return: 提取的作者信息（字典格式）
        :raises: ValueError 如果响应格式不正确
        :raises: Exception 如果API调用失败
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-3.5-turbo"
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts author information from academic papers. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000,
                n=1,
                timeout=30
            )
            
            if not response.choices:
                raise Exception("Empty response from OpenAI")
            
            content = response.choices[0].message.content
            # Remove any markdown formatting if present
            content = content.replace('```json', '').replace('```', '').strip()
            
            # print(f"This is : {content}")
            
            # Parse and validate JSON response
            try:
                extracted_data = json.loads(content)
                
                # Validate expected fields
                if isinstance(extracted_data, dict):
                    return extracted_data
                else:
                    raise ValueError("Response is not a valid JSON object")
                    
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON response: {content}")
                
        except ValueError as e:
            # Re-raise ValueError for invalid API key or response format
            raise
        except Exception as e:
            print(f"Error in LLM call: {str(e)}")
            raise

    # 提取作者信息
    def extract_author_info(self, author_list: List[str]) -> Dict:
        
        """
        从文本中提炼作者信息，默认作者信息在文本靠前部分。
        假设作者信息包含名字、邮箱、学校等信息
        author_names: 字符串，逗号分隔。已知的名字，可以作为输入，作为大模型推理的上下文
        :return: 返回提炼出的作者信息, 以JSON格式返回
        """
        authors_info = []
        author_str = ", ".join(author_list)

        # 提取PDF的title 和abstraction 之前的文字
        author_context = self._extract_text_before_abstract()
        
        try:
            # Single LLM call for all authors
            prompt = self.AUTHOR_AFFILIATION_PROMPT_TEMPLATE.substitute(
                context=author_context,
                author_names=author_str
            )
            
            extracted_data = self._call_llm(prompt)
            
            # Create institution lookup dictionary
            institution_lookup = {
                inst["id"]: inst["name"] 
                for inst in extracted_data.get("institutions", [])
            }
            
            # Process each author's affiliations
            for idx, author_data in enumerate(extracted_data.get("author_affiliations", [])):
                # Get institution names for this author's affiliation IDs
                affiliations = [
                    institution_lookup.get(aff_id, "Not Found")
                    for aff_id in author_data.get("affiliation_ids", [])
                ]
                
                # If no affiliations found, use ["Not Found"]
                if not affiliations:
                    affiliations = ["Not Found"]

                email = author_data.get("email")
                
                author_info = {
                    "name": author_data["name"],
                    "affiliations": affiliations,
                    "email": email,
                    "sequence": idx,
                    "is_corresponding": (idx == 0)
                }
                authors_info.append(author_info)
            
            return authors_info
            
        except Exception as e:
            print(f"Error extracting affiliations: {str(e)}")
            # Fallback: create basic info for all authors
            return [
                {
                    "name": name,
                    "affiliations": ["Not Found"],
                    "sequence": idx,
                    "is_corresponding": (idx == 0)
                }
                for idx, name in enumerate(author_list)
            ]

    def extract_references_info(self) -> Dict:
        """
        从文本中提炼参考文献信息，默认参考文献在文本靠后部分。
        假设参考文献信息包含标题、作者、年份等信息
        :return: 返回提炼出的参考文献信息, 以JSON格式返回
        """
        references_info = []
        references_context = self._extract_text_after_references()
        
        try:
            # Single LLM call for all references
            prompt = self.REFERENCES_PROMPT_TEMPLATE.substitute(
                context=references_context
            )
            
            extracted_data = self._call_llm(prompt)
            
            # Process each reference
            for reference_data in enumerate(extracted_data.get("references", [])):
                reference_info = {
                    "title": reference_data.get("title", "Not Found"),
                    "authors": reference_data.get("authors", ["Not Found"]),
                    "year": reference_data.get("year", "Not Found"),
                    "journal": reference_data.get("journal", "Not Found"),
                }
                references_info.append(reference_info)
            
            return references_info
            
        except Exception as e:
            print(f"Error extracting references: {str(e)}")
            # Fallback: create basic info for all references
            return [
                {
                    "title": "Not Found",
                    "authors": ["Not Found"],
                    "year": "Not Found",
                    "journal": "Not Found",
                }
                for idx in range(10)
            ]


