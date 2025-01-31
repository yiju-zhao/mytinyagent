import os

# 数据库配置
DB_USER = "admin"
DB_PASSWORD = "admin123"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "research_db"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 目录配置
CSV_FILE_PATH = os.path.join("data", "papers_metadata.csv")
PDF_FOLDER_PATH = os.path.join("data", "pdfs")