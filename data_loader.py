import pandas as pd
from config import CSV_FILE_PATH

def load_paper_metadata():
    df = pd.read_csv(CSV_FILE_PATH)
    papers = []
    for _, row in df.iterrows():
        papers.append({
            "title": row["title"],
            "url": row.get("url", None),
            "authors": [author.strip() for author in row["author"].split(";")]
        })
    return papers