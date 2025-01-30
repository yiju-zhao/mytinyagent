/*
  Table Definition: conference
  ----------------------------
  - conference_id (SERIAL): 自动增长的主键，唯一标识每个会议
  - name (VARCHAR): 会议名称，必须唯一
  - type (VARCHAR): 会议类型（如 academia, industry 等）
  - description (TEXT): 会议的描述，提供关于会议的详细信息
*/

-- conference table create
CREATE TABLE conference (
    conference_id SERIAL PRIMARY KEY,  -- 自增主键
    name VARCHAR(255) NOT NULL,        -- 会议名称，最长 255 个字符，不能为空
    type VARCHAR(255) NOT NULL,        -- 会议类型，不能为空，例如 academia, industry 等
    description TEXT,                  -- 会议描述，TEXT 类型适合存储长文本
    CONSTRAINT unique_conference_name UNIQUE (name)  -- 确保会议名称唯一
);

-- Create unique index on name to enforce uniqueness at the database level
CREATE UNIQUE INDEX idx_conference_name ON conference (name);

-- test insert
INSERT INTO conference (name, type, description)
VALUES ('NeurIPS', 'Academia', '神经信息处理系统大会（NeurIPS）是一个机器学习和计算神经科学领域的年度学术会议，每年12月举行。');

-- test insert
SELECT * FROM conference LIMIT 10;

/*
  Table Definition: conference_instance
  ------------------------------------
  - primary key: instance_id (SERIAL): 自动增长的唯一标识符
  - name (VARCHAR): 会议名称，必须唯一
  - conference_id (INTEGER): 关联 `conference` 表的外键
  - year (INTEGER): 表示该会议举办的年份
  - start_date (DATE): 会议开始日期
  - end_date (DATE): 会议结束日期
  - location (VARCHAR): 会议举办地点
  - website (VARCHAR): 会议官网链接
*/
CREATE TABLE conference_instance (
    instance_id SERIAL PRIMARY KEY,    -- 自增主键
    name VARCHAR(255) NOT NULL UNIQUE,  -- 会议实例名称，唯一
    conference_id INTEGER NOT NULL,     -- 关联的 `conference` 表
    year INTEGER NOT NULL,              -- 会议举办年份
    start_date DATE,           -- 会议开始日期
    end_date DATE,             -- 会议结束日期
    location VARCHAR(255),              -- 会议举办地点
    website VARCHAR(255),               -- 会议官网链接
    CONSTRAINT fk_conference FOREIGN KEY (conference_id) REFERENCES conference(conference_id) -- 外键关联
);

-- test insert
INSERT INTO conference_instance (name, conference_id, year, start_date, end_date, location, website)
VALUES 
('NeurIPS 2025', 1, 2025, '2025-12-01', '2025-12-05', 'Vancouver, Canada', 'https://nips.cc/2025');

-- test select
SELECT * FROM conference_instance;

SELECT ci.instance_id, ci.name, ci.year, ci.start_date, ci.end_date, ci.location, ci.website, c.name AS conference_name
FROM conference_instance ci
JOIN conference c ON ci.conference_id = c.conference_id;

/*
  Table Definition: paper
  ------------------------
  - paper_id (SERIAL): 自动增长的主键，唯一标识每篇论文
  - instance_id (INTEGER): 关联 `conference_instance` 表，表示该论文属于哪个会议实例
  - title (VARCHAR): 论文标题
  - type (VARCHAR): 论文类型（如 oral, poster, 等）
  - year (INTEGER): 论文的出版年份
  - publish_date (DATE): 论文的发布日期
  - TLDR (TEXT): 论文的简短总结，一句话概括论文内容
  - abstract (TEXT): 论文摘要，提供论文的简要内容
  - content (TEXT): 论文的完整文本内容
  - pdf_path (VARCHAR): 论文 PDF 的文件路径或 URL
  - citation_count (INTEGER): 论文的引用次数
  - award (VARCHAR): 论文获奖情况（如 best paper, best paper runner 等，可以由逗号分隔）
  - Digital Object Identifier
  - Link to code repository: 论文代码库链接
  - Link to support materials: 补充材料链接
*/

-- paper table create
CREATE TABLE paper (
    paper_id SERIAL PRIMARY KEY,          -- 自增主键
    instance_id INTEGER NOT NULL,         -- 关联的 `conference_instance` 表的 ID
    title VARCHAR(255) NOT NULL,          -- 论文标题，不能为空
    type VARCHAR(50),                     -- 论文类型，例如 oral, poster
    year INTEGER NOT NULL,                -- 论文出版年份
    publish_date DATE,                    -- 论文发布日期
    TLDR TEXT,                            -- 论文简短总结
    abstract TEXT,                        -- 论文摘要
    content TEXT,                         -- 论文完整内容
    pdf_path VARCHAR(255),                -- 论文 PDF 路径或 URL
    citation_count INTEGER DEFAULT 0,     -- 论文引用次数，默认为 0
    award VARCHAR(255),                   -- 获奖情况（例如 best paper, best paper runner）
    doi VARCHAR(255),                      -- Digital Object Identifier
    code_url VARCHAR(255),                 -- Link to code repository
    supplementary_material_url VARCHAR(255), -- Link to supplementary materials
    CONSTRAINT fk_instance FOREIGN KEY (instance_id) REFERENCES conference_instance(instance_id) -- 外键关联
);

-- Create an index on title for faster search on paper titles
CREATE INDEX idx_paper_title ON paper (title);

-- test 
INSERT INTO paper (instance_id, title, type, year, publish_date, TLDR, abstract, content, pdf_path, citation_count, award)
VALUES 
(1, 
 'Neural Networks for AI', 
 'Oral', 
 2025, 
 '2025-12-02', 
 'This paper explores the use of neural networks in AI applications.', 
 'The paper investigates several advanced neural network architectures and their applications in artificial intelligence fields such as natural language processing and computer vision.', 
 'The detailed content of the paper goes here...', 
 'https://example.com/paper/neural-networks-for-ai.pdf', 
 25, 
 'Best Paper');
SELECT * FROM paper;


-- 添加向量检索的支持
CREATE EXTENSION IF NOT EXISTS vector;

/*
  Table Definition: content_embedding
  ------------------------
  - embedding_id (SERIAL): 自增的主键，唯一标识每个向量
  - paper_id (INTEGER): 外键，关联到 paper 表，表示该向量化内容属于哪篇论文
  - embedding (VECTOR(768)): 存储 768 维的论文内容向量
*/
CREATE TABLE content_embedding (
    embedding_id SERIAL PRIMARY KEY,                -- 自增主键
    paper_id INTEGER NOT NULL,                      -- 关联的论文 ID
    embedding VECTOR(768),                          -- 论文内容的 768 维向量
    CONSTRAINT fk_paper FOREIGN KEY (paper_id) REFERENCES paper(paper_id) ON DELETE CASCADE  -- 外键关联，删除论文时级联删除
);

-- 创建 HNSW 索引以加速向量相似度检索（余弦相似度）
CREATE INDEX ON content_embedding USING hnsw (embedding vector_cosine_ops);

-- test
SELECT embedding FROM content_embedding WHERE paper_id = 1;

/*
  Table Definition: author
  ------------------------
  - author_id (SERIAL): 自动增长的主键，唯一标识作者
  - name (VARCHAR): 作者名字
  - email (VARCHAR): 邮箱
  - google_scholar_url (VARCHAR): 作者的 Google Scholar 主页
  - home_website (VARCHAR): 个人主页
  - nationality (VARCHAR): 国籍
*/

-- author table create
CREATE TABLE author (
    author_id SERIAL PRIMARY KEY,               -- 自增主键
    name VARCHAR(255) NOT NULL,                  -- 作者名字
    email VARCHAR(255),                          -- 邮箱
    google_scholar_url VARCHAR(255),             -- Google Scholar 主页
    home_website VARCHAR(255),                   -- 个人主页
    nationality VARCHAR(100)                     -- 国籍
);

/*
  Table Definition: paper_authors
  ------------------------
  - Links papers with their authors, including author order
  - paper_id (INTEGER): Foreign key to paper table
  - author_id (INTEGER): Foreign key to author table
  - author_order (INTEGER): Order of authors in the paper
*/

--paper_authors table create
CREATE TABLE paper_authors (
    paper_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    author_order INTEGER NOT NULL,  -- Position in author list (1 for first author, etc.)
    is_corresponding BOOLEAN DEFAULT FALSE,  -- Indicates if this is the corresponding author
    PRIMARY KEY (paper_id, author_id),
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES author(author_id) ON DELETE CASCADE
);


/*
  Table Definition: affiliation
  ------------------------
  - affiliation_id (SERIAL): 自动增长的主键，唯一标识 affiliation
  - name (VARCHAR): affiliation 名称
  - type (VARCHAR): 如 university, industry, research lab 等
  - location (VARCHAR): 组织的地点
  - website (VARCHAR): 主页
  - description (TEXT): 描述
*/

-- affiliation table create
CREATE TABLE affiliation (
    affiliation_id SERIAL PRIMARY KEY,           -- 自增主键
    name VARCHAR(255) NOT NULL,                   -- 组织名称
    type VARCHAR(100) NOT NULL,                   -- 类型（如 university, industry 等）
    location VARCHAR(255),                        -- 组织地点
    website VARCHAR(255),                         -- 网站
    description TEXT                              -- 描述
);

/*
  Table Definition: author_affiliation
  ------------------------
  - author_id (INTEGER): 关联到 author 表
  - affiliation_id (INTEGER): 关联到 affiliation 表
*/

-- author_affiliation table create (多对多关系)
CREATE TABLE author_affiliation (
    author_id INTEGER NOT NULL,                  -- 关联的作者 ID
    affiliation_id INTEGER NOT NULL,             -- 关联的组织 ID
    PRIMARY KEY (author_id, affiliation_id),     -- 组合主键，确保一个作者在一个组织中只能出现一次
    CONSTRAINT fk_author FOREIGN KEY (author_id) REFERENCES author(author_id) ON DELETE CASCADE,   -- 外键约束，删除作者时级联删除
    CONSTRAINT fk_affiliation FOREIGN KEY (affiliation_id) REFERENCES affiliation(affiliation_id) ON DELETE CASCADE  -- 外键约束，删除组织时级联删除
);

-- test
-- 插入作者数据
INSERT INTO author (name, email, google_scholar_url, home_website, nationality)
VALUES 
('张三', 'zhang.san@example.com', 'https://scholar.google.com/zhangsan', 'https://zhangsan.com', 'China'),
('张三', 'zhang.san2@example.com', 'https://scholar.google.com/zhangsan2', 'https://zhangsan2.com', 'China');

-- 插入组织数据
INSERT INTO affiliation (name, type, location, website, description)
VALUES 
('XYZ University', 'University', 'New York, USA', 'https://xyzuniversity.edu', 'A top university specializing in AI research'),
('TechCorp', 'Industry', 'Toronto, Canada', 'https://techcorp.com', 'A leading company in AI-powered technology');

-- 插入作者与组织的关系
INSERT INTO author_affiliation (author_id, affiliation_id)
VALUES 
(1, 1),   -- 张三 -> XYZ University
(2, 2);   -- 张三 -> TechCorp

-- select 
SELECT a.name AS author_name, aff.name AS affiliation_name
FROM author a
JOIN author_affiliation aa ON a.author_id = aa.author_id
JOIN affiliation aff ON aa.affiliation_id = aff.affiliation_id;

SELECT a.name AS author_name
FROM author a
JOIN author_affiliation aa ON a.author_id = aa.author_id
JOIN affiliation aff ON aa.affiliation_id = aff.affiliation_id
WHERE aff.name = 'XYZ University';

/*
  Table Definition: keyword
  ------------------------
  - keyword_id (SERIAL): 自增的主键，唯一标识每个关键字
  - keyword (VARCHAR(255)): 关键字的名称，最大长度为 255，保证唯一性，不允许为空
  - description (TEXT): 关键字的描述，提供有关该关键字的更多信息，可以为空
*/
CREATE TABLE keyword (
    keyword_id SERIAL PRIMARY KEY,  -- 自增的主键，唯一标识每个关键字
    keyword VARCHAR(255) UNIQUE NOT NULL,  -- 关键字名称，长度限制为 255，确保唯一性，不能为空
    description TEXT  -- 关键字的描述，可以是关于关键字的详细信息
);

-- 创建论文和关键字的多对多关系中间表
CREATE TABLE paper_keywords (
    paper_id INT NOT NULL,  -- 论文ID，关联到 paper 表
    keyword_id INT NOT NULL,  -- 关键字ID，关联到 keyword 表
    PRIMARY KEY (paper_id, keyword_id),  -- 组合主键，确保论文与关键字的唯一组合
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id) ON DELETE CASCADE,  -- 论文删除时，相关记录删除
    FOREIGN KEY (keyword_id) REFERENCES keyword(keyword_id) ON DELETE CASCADE  -- 关键字删除时，相关记录删除
);

-- test
-- 向 keyword 表插入数据
INSERT INTO keyword (keyword, description) 
VALUES 
('Machine Learning', 'A field of computer science that uses algorithms to learn from data'),
('Deep Learning', 'A subfield of machine learning that uses neural networks with many layers');

-- 关联论文与关键字
INSERT INTO paper_keywords (paper_id, keyword_id) 
VALUES 
(1, (SELECT keyword_id FROM keyword WHERE keyword = 'Machine Learning')),
(1, (SELECT keyword_id FROM keyword WHERE keyword = 'Deep Learning'));

-- 查询论文的所有关键字
SELECT p.paper_id, p.title, k.keyword 
FROM paper p
JOIN paper_keywords pk ON p.paper_id = pk.paper_id
JOIN keyword k ON pk.keyword_id = k.keyword_id
WHERE p.paper_id = 1;  -- 假设查询 ID 为 1 的论文

/*
  Table Definition: reference
  ------------------------
  - reference_id (SERIAL): 自增的主键，唯一标识每条参考文献
  - title (VARCHAR(255)): 参考文献的标题，最大长度为 255，不能为空
  - author (TEXT): 参考文献的作者，多个作者用逗号分隔，可以为空
  - year (INTEGER): 参考文献的出版年份
  - journal (VARCHAR(255)): 参考文献所属期刊名称，如果来自期刊的话
  - web_url (VARCHAR): 参考文献的网页 URL 或指向原始论文的 URL
*/
CREATE TABLE reference (
    reference_id SERIAL PRIMARY KEY,  -- 自增的主键，唯一标识每条参考文献
    title VARCHAR(255) NOT NULL,  -- 参考文献标题，不能为空
    author TEXT,  -- 作者，多个作者用逗号分隔，可以为空
    year INTEGER,  -- 参考文献出版年份
    journal VARCHAR(255),  -- 参考文献所属期刊名称
    web_url VARCHAR(255)  -- 参考文献的网页 URL 或指向原始论文的 URL
);

/*
  Table Definition: paper_references
  ------------------------
  - paper_id (INTEGER): 外键，关联到 paper 表，表示该论文引用了哪篇参考文献
  - reference_id (INTEGER): 外键，关联到 reference 表，表示被引用的参考文献
  - PRIMARY KEY (paper_id, reference_id): 组合主键，确保每篇论文引用同一参考文献的唯一性
*/
CREATE TABLE paper_references (
    paper_id INT NOT NULL,  -- 论文 ID，关联到 paper 表
    reference_id INT NOT NULL,  -- 参考文献 ID，关联到 reference 表
    PRIMARY KEY (paper_id, reference_id),  -- 组合主键，确保唯一性
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id) ON DELETE CASCADE,  -- 论文删除时，相关记录也会删除
    FOREIGN KEY (reference_id) REFERENCES reference(reference_id) ON DELETE CASCADE  -- 参考文献删除时，相关记录也会删除
);
-- test
-- 插入一条参考文献数据
INSERT INTO reference (title, author, year, journal, web_url)
VALUES 
('Understanding Deep Learning', 'Yann LeCun, Geoffrey Hinton, Yoshua Bengio', 2015, 'Nature', 'https://example.com/paper1'),
('A Survey of Reinforcement Learning', 'Richard S. Sutton, Andrew G. Barto', 2018, 'Journal of AI Research', 'https://example.com/paper2');

-- 将论文与参考文献关联
INSERT INTO paper_references (paper_id, reference_id)
VALUES 
(1, 1),  -- 论文 1 引用参考文献 1
(1, 2);  -- 论文 1 引用参考文献 2

-- 查询论文的所有参考文献
SELECT p.paper_id, p.title, r.title AS reference_title, r.author, r.year, r.journal, r.web_url
FROM paper p
JOIN paper_references pr ON p.paper_id = pr.paper_id
JOIN reference r ON pr.reference_id = r.reference_id
WHERE p.paper_id = 1;  -- 假设查询论文 ID 为 1 的所有参考文献


/*
  Table Definition: paper_reviews
  ------------------------
  - Stores reviews and comments about papers
*/
CREATE TABLE paper_reviews (
    review_id SERIAL PRIMARY KEY, -- 主键，唯一标识每篇审稿
    paper_id INTEGER NOT NULL, -- 论文 ID，关联到 paper 表
    reviewer_id INTEGER,  -- NULL for 匿名评审
    review_text TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES author(author_id) ON DELETE SET NULL
);
