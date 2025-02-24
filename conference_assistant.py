import ast
import logging
import os
import re
import pandas as pd
from datetime import datetime

import requests

from db_manager import DBManager
from llm.ollama_model import OllamaModel
from models import Affiliation, Author, Keyword, Paper, Reference
from paper_agent import PDFAnalyzer
from repositories import (
    AuthorRepository,
    PaperRepository,
    KeywordRepository,
    ConferenceRepository,
    ConferenceInstanceRepository,
    EmbeddingRepository
)
from repositories import EmbeddingRepository


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUCCESS_LOG_PATH = "./data/logs/success_log.csv"
ERROR_LOG_PATH = "./data/logs/error_log.csv"

class ConferenceAssistant:
    def __init__(
        self, 
        year:           int,
        conference:     str,
        location:       str,
        website:        str,
        category:       str,
        description:    str,
        input_file:     str,
        start_date:     datetime,
        end_date:       datetime
    ):
        global success_logs_df, error_logs_df
        self.year           = year
        self.conference     = conference
        self.start_date     = start_date
        self.end_date       = end_date
        self.location       = location
        self.website        = website
        self.category       = category
        self.description    = description
        self.csv_file_path  = input_file
        self.instance_id    = None
        self.db_manager     = DBManager()
        self.llm = OllamaModel()
        self.base_pdf_dir = f"./data/pdfs/{str(self.conference).strip().lower()}/{str(self.year)}/"
        self.success_logs_df = pd.DataFrame(columns=["index", "title"])
        self.error_logs_df = pd.DataFrame(columns=["index", "title", "step", "error_message"])
        
    def upsert_conference(self):
        session = self.db_manager.get_session()
        conference_repo = ConferenceRepository(session)
        conf = conference_repo.upsert(
            name=self.conference,
            type=self.category,
            description=self.description
        )
        self.conference_id = conf.conference_id
        session.close()

    def upsert_instance(self):
        session = self.db_manager.get_session()
        instance_repo = ConferenceInstanceRepository(session)
        instance = instance_repo.upsert(
            conference_id=self.conference_id,
            name=self.conference,
            year=self.year,
            start_date=self.start_date,
            end_date=self.end_date,
            location=self.location,
            website=self.website
        )
        self.instance_id = instance.instance_id
        session.close()

    def upsert_paper(self):
        # Get a database session from the DBManager
        session = self.db_manager.get_session()
        author_repo = AuthorRepository(session)
        paper_repo = PaperRepository(session)
        keyword_repo = KeywordRepository(session)

        collection = self.db_manager.get_vdb_collection()
        embedding_repo = EmbeddingRepository(collection)

        metadata = pd.read_csv(self.csv_file_path)
        
        stage_records = []
        # Iterate through each row in the DataFrame
        for index, row in metadata.iterrows():
            try:
                stage_records.append('start')
                paper_title = row.get("paper_title")
                self.print_start_separator(index=index, title=paper_title)
                if index == 2:
                    break
                
                paper = paper_repo.get_papers(limit=1, offset=None, 
                                                    title=paper_title, instance_id=self.instance_id)
                if paper:
                    logger.warning(
                        f"Found a paper in database with the same title and conference instance. "
                        f"This is not expected, skipping.\nTitle: {paper_title}, Instance ID: {self.instance_id}"
                    )
                    self.write_success(index=index, title=paper_title, message='duplicated with existing db, skipped')
                    continue
                
                logger.info(f"this paper is a new paper, saving into the database... titile={paper_title}")
                # Extract data from the row
                # 初始化 Paper 对象并填充基本属性
                # paper_title,author_ids,author_names,venue,research_area,
                # keywords,tldr,abstract,url,pdf_url,attachment_url,pdf_path
                new_paper = Paper(
                    title=paper_title,
                    instance_id=self.instance_id,
                    year=int(row.get('year')) if row.get("year") else self.year,
                    venue=row.get('venue'),
                    research_area=row.get('research_area'),
                    tldr=row.get('tldr'),
                    abstract=row.get('abstract'),
                    pdf_path=row.get('pdf_path'),
                    url=row.get('url'),
                    pdf_url=row.get('pdf_url'),
                    attachment_url=row.get('attachment_url'),
                )
                stage_records.append('Paper instance 初始化完成。下一步处理PDF文件')
                # download the pdf to the directory if can not find it
                if not self.is_valid_pdf_path(new_paper.pdf_path):
                    new_paper.pdf_path = self.download_pdf_direct(pdf_title=new_paper.title, 
                                                                pdf_url=new_paper.pdf_url)
                
                stage_records.append('Paper 文件已下载。准备调用PDFAnalyzer')
                # 调用 PDFAnalyzer 提取更多信息
                author_names = ast.literal_eval(row.get('author_names')) if not row.get('author_names') else []
                author_ids = ast.literal_eval(row.get('author_ids')) if not row.get('author_ids') else []

                pdf_analyzer = PDFAnalyzer(
                    title=new_paper.title,
                    abstract=new_paper.abstract or "",
                    author_names=author_names,
                    author_ids=author_ids,
                    pdf_path=new_paper.pdf_path,
                    tldr=new_paper.tldr or "",
                    keywords=new_paper.research_area or "",
                    llm=self.llm  # 假设 self.llm 是 BaseLLM 实例
                )

                # TODO
                pdf_analyzer.parse_all()
                stage_records.append('对pdf文件的解析完成，parse_all 完成。准备提取数据')
                # 提取完整文本
                new_paper.content_raw_text = pdf_analyzer.text
                print(new_paper.content_raw_text[:20])
                
                new_paper.conclusion = pdf_analyzer.conclusion

                # 处理作者信息
                author_dict = pdf_analyzer.authors_augmented_info_dict
                author_instances = []
                for author in author_dict:
                    # 查找作者是否已经存在
                    if author.get('author_id'):
                        existing_author = session.query(Author).filter_by(external_id=author.get('author_id')).first()
                        if existing_author:
                            author_instances.append(existing_author)
                            continue
                    
                    # 如果作者不存在，则创建新的作者对象
                    new_author = Author(name=author.get('name'),
                                        external_id=author.get('author_id'),
                                        email=author.get('email','unknown'),
                                        nationality=author.get('nationality','unknown')
                        )
                    
                    # 处理组织关系
                    affiliation_instances =[]
                    if author.get('affiliation'):
                        for affiliation_name in author.get('affiliation'):
                            existing_affiliation = session.query(Affiliation).filter_by(name=affiliation_name).first()
                            if not existing_affiliation:
                                new_affiliation = Affiliation(name=affiliation_name)
                                affiliation_instances.append(new_affiliation)
                                session.add(new_affiliation)
                            else:
                                affiliation_instances.append(existing_affiliation)
                    
                    for affiliation_instance in affiliation_instances:
                        new_author.affiliation_to_author.append(affiliation_instance)
                    
                    session.add(new_author)
                    author_instances.append(new_author)
                    
                for author_instance in author_instances:
                    new_paper.author_to_paper.append(author_instance)
                
                stage_records.append('作者信息提取完成')
                # 处理关键字
                print(pdf_analyzer.keywords)
                keyword_instances = []
                for item in pdf_analyzer.keywords:
                    for keyword_name in item.get('keywords',[]):
                        # 查找是否存在相同的关键字
                        existing_keyword = session.query(Keyword).filter_by(keyword=keyword_name).first()
                        if not existing_keyword:
                            # 如果没有找到，创建新的 Keyword 实例
                            new_keyword = Keyword(keyword=keyword_name)
                            session.add(new_keyword)
                            keyword_instances.append(new_keyword)  # 将新创建的关键词加入实例列表
                        else:
                            # 如果找到了，使用已存在的 Keyword 实例
                            keyword_instances.append(existing_keyword)
                # 将 Paper 和 Keyword 之间的多对多关系插入 `paper_keyword` 中间表
                for keyword_instance in keyword_instances:
                    new_paper.keyword_to_paper.append(keyword_instance)
                stage_records.append('作者信息提取完成')
                
                # 提取abstract, 原来的metadata没有的话
                if not new_paper.abstract or not new_paper.abstract.strip():
                    new_paper.abstract = pdf_analyzer.abstract

                stage_records.append('abstract提取完成')
                
                # reference 耗时太久了，因此，可以考虑先存储reference 文本
                reference_instances = []
                for reference in pdf_analyzer.references_list:
                    existing_reference = session.query(Reference).filter_by(title=reference.get('title')).first()
                    if not existing_reference:
                        new_reference = Reference(
                            title=reference.get('title'),
                            author=reference.get('author'),
                            year=reference.get('year'),
                            journal=reference.get('journal'),
                            web_url=reference.get('web_url')
                        )
                        session.add(new_reference)
                        reference_instances.append(new_reference)
                    else:
                        reference_instances.append(existing_reference)
                
                for reference_instance in reference_instances:
                    new_paper.reference_to_paper.append(reference_instance)
                stage_records.append('reference 处理完成')
                # 最后提交事务，将数据保存到数据库
                session.add(new_paper)
                session.commit()
                stage_records.append('数据库提交处理完成')
                logger.info(f"<<<<<<<<Paper '{new_paper.title}' inserted successfully with ID: {new_paper.paper_id}.<<<<<")            
                
                # 向数据库中插入或更新论文
                logger.info(f">>>>>>>insert embedding of Paper '{new_paper.title}' with ID: {new_paper.paper_id}.>>>>>>>>")  
                embedding_repository = EmbeddingRepository(self.db_manager.get_vdb_collection())
                embedding_repository.insert_chunks_batch(int(new_paper.paper_id), pdf_analyzer.embedding_list)
                stage_records.append('向量数据库提交处理完成')
                
                self.write_success(index, paper_title, 'all good!')
                self.print_end_separator(index=index, title=paper_title)        
            except Exception as e:
                logger.error(f'failed to process pdf file: {index}, {paper_title}, error: {str(e)}')
                self.write_error(index, paper_title, step='\n'.join(stage_records),error_message=str(e))
            
        session.close()
        # 在适当的时候调用 flush_logs 一次性写入
        self.flush_logs()
        logger.info("!!!!!!!!!  upsert_paper end     !!!!!!!!.")


    def parse_title_to_filename(self, title):
        # Remove any non-alphanumeric characters and replace spaces with underscores
        filename = re.sub(r'\W+', '_', title)
        return filename + '.pdf'

    # Function to download a PDF given a URL
    def download_pdf_direct(self, pdf_title, pdf_url):
        try:
            # 验证 pdf_title
            if not isinstance(pdf_title, str) or not pdf_title.strip():
                raise ValueError("PDF title is not valid.")
            
            pdf_filename = self.parse_title_to_filename(pdf_title)
            pdf_path = os.path.join(self.base_pdf_dir, pdf_filename)

            if os.path.exists(pdf_path):
                logger.info(f"PDF already exists: {pdf_path}")
                return pdf_path
            else:
                logger.info(f"PDF not found. Downloading to {pdf_path}...")
                # Make a request to the URL
                response = requests.get(pdf_url)
                response.raise_for_status()  # Raise an error for bad responses
                
                # Save the PDF file locally
                with open(pdf_path, 'wb') as file:
                    file.write(response.content)
                
                print(f"PDF downloaded successfully to {pdf_path}")
                return pdf_path

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while downloading the PDF: {e}")
            return False

    def is_valid_pdf_path(sefl, pdf_path: str) -> bool:
        # 类型和非空检查
        if not isinstance(pdf_path, str) or not pdf_path.strip():
            logger.error("pdf_path must be a non-empty string.")
            return False

        # 清理路径 (去除多余空格)
        pdf_path = pdf_path.strip()

        # 路径合法性检查
        # 检查是否含有非法路径穿越模式
        if ".." in pdf_path or pdf_path.startswith(("/", "\\")):
            logger("pdf_path contains invalid traversal or absolute path.")
            return False


    def write_success(self, index, title, message):
        """写入成功记录（累积在内存中）"""
        new_row = pd.DataFrame([{"index": index, "title": title, "message": message}])
        self.success_logs_df = pd.concat([self.success_logs_df, new_row], ignore_index=True)

    def write_error(self, index, title, step, error_message):
        """写入错误记录（累积在内存中）"""
        new_row = pd.DataFrame([{"index": index, "title": title, "step": step, "error_message": error_message}])
        self.error_logs_df = pd.concat([self.error_logs_df, new_row], ignore_index=True)

    def flush_logs(self):
        """将所有内存中的记录一次性写入文件"""
        if not self.success_logs_df.empty:
            self.success_logs_df.to_csv(SUCCESS_LOG_PATH, mode="a", header=not pd.io.common.file_exists(SUCCESS_LOG_PATH), index=False)
        if not self.error_logs_df.empty:
            self.error_logs_df.to_csv(ERROR_LOG_PATH, mode="a", header=not pd.io.common.file_exists(ERROR_LOG_PATH), index=False)

    
    def print_start_separator(self, index, title):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = (
            "\n" +
            "=" * 70 + "\n"
            f"🚀 [START PROCESSING] 🚀\n"
            f"📄 Index: {index}\n"
            f"📑 Title: \"{title}\"\n"
            f"🕒 Timestamp: {timestamp}\n"
            + "=" * 70
        )
        logger.info(separator)

    def print_end_separator(self, index, title):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = (
            "\n" +
            "=" * 70 + "\n"
            f"✅ [PROCESS COMPLETED] ✅\n"
            f"📄 Index: {index}\n"
            f"📑 Title: \"{title}\"\n"
            f"🕒 Finished at: {timestamp}\n"
            + "=" * 70
        )
        logger.info(separator)
        
    def run(self):
        self.upsert_conference()
        self.upsert_instance()
        self.upsert_paper()