# IKB-Agent

智能知识库系统（RAG 文档处理平台），面向企业产品手册、维修文档、课件资料和 Markdown 知识库等场景，提供文档导入、PDF 解析、语义切分、商品识别、向量入库、混合检索和 RAG 问答演示。

项目参考企业级 RAG 文档处理链路实现，支持轻量本地演示，也支持 Docker 中间件版部署。面试时可以把它讲成一个“给 AI Agent 和问答系统提供高质量知识数据源”的文档处理平台。

## 功能特性

- 支持 PDF / Markdown / TXT 上传导入。
- 支持两种 PDF 解析模式：
  - `pypdf`：轻量文本抽取，速度快，适合本地演示和文本型 PDF。
  - `mineru`：调用 MinerU 解析复杂 PDF，支持版面、表格、图片和 OCR，准确度更高但耗时更长。
- 基于 LangGraph 编排导入链路，覆盖入口识别、PDF 转 Markdown、图片语义化、文档切分、商品识别、Embedding 和向量入库。
- 实现标题层级切分 + 递归切分 + 短片段合并，尽量减少语义割裂。
- 基于 LLM 或启发式逻辑提取商品名，并回填到所有 Chunk 元数据中。
- 支持 Dense + Sparse 混合检索；本地默认使用轻量向量化，生产形态可替换为 BGE-M3。
- 支持 JSON 本地存储，也可以切换到 Milvus、MongoDB、MinIO 等中间件。
- 提供 FastAPI 接口和前端工作台页面，支持导入任务状态、执行链路和问答结果查看。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Web 服务 | FastAPI, Uvicorn |
| 流程编排 | LangGraph |
| PDF 解析 | pypdf, MinerU |
| 大模型 | DashScope / OpenAI-compatible API, Qwen 系列模型 |
| 向量检索 | BGE-M3 / 本地 Dense-Sparse, Milvus |
| 对象存储 | MinIO |
| 任务记录 | JSON, MongoDB |
| 前端 | HTML, CSS, JavaScript |
| 部署 | Docker Compose |

## 架构流程

导入链路：

```text
Document Upload
  -> EntryNode
  -> PdfToMarkdownNode / MarkdownLoadNode
  -> MarkdownImageNode
  -> DocumentSplitNode
  -> ItemNameRecognitionNode
  -> EmbeddingNode
  -> ImportStoreNode
```

查询链路：

```text
User Query
  -> 商品名推断
  -> Dense/Sparse 混合检索
  -> Top-K 证据片段
  -> 可追溯答案
```

## 快速启动：轻量测试版

轻量版不强制依赖 Docker、Milvus、MinIO、MongoDB 或外部大模型，适合先快速跑通项目。

```bash
git clone https://github.com/Yin123-ybh/IKB-Agent.git
cd IKB-Agent

python -m venv .venv
source .venv/bin/activate

pip install -e ".[pdf]"
uvicorn ikb_agent.main:app --reload
```

打开：

```text
http://127.0.0.1:8000
```

页面中选择“轻量版 pypdf”，上传 PDF / Markdown / TXT 后即可检索问答。

## Docker 中间件版

如果希望展示更接近课件和生产环境的版本，可以启动 Milvus、Etcd、MinIO、Attu 和 MongoDB：

```bash
docker compose up -d
docker compose ps
```

安装中间件依赖：

```bash
source .venv/bin/activate
pip install -e ".[pdf,middleware]"
python scripts/test_connections.py
```

`.env` 推荐配置：

```env
STORE_BACKEND=milvus
MILVUS_URL=http://localhost:19530
MONGO_URL=mongodb://localhost:27017
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=ikb-agent
```

常用访问地址：

```text
Milvus:        localhost:19530
Milvus Health: http://127.0.0.1:9091/healthz
MinIO Console: http://127.0.0.1:9001
Attu:          http://127.0.0.1:7001
MongoDB:       mongodb://localhost:27017
```

## MinerU 解析模式

MinerU 依赖较重，建议使用 Python 3.12 虚拟环境安装。Python 3.14 环境可能无法安装部分依赖。

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate

pip install -e ".[pdf,middleware,mineru]"
python scripts/check_mineru.py
uvicorn ikb_agent.main:app --reload
```

`.env` 推荐配置：

```env
PDF_PARSE_BACKEND=pypdf
MINERU_CLI=mineru
MINERU_METHOD=auto
MINERU_BACKEND=pipeline
MINERU_SOURCE=local
MINERU_FORMULA=false
MINERU_TABLE=true
MINERU_IMAGE_ANALYSIS=true
```

说明：

- 页面上传时可以为单个文件选择 `pypdf` 或 `mineru`，优先级高于 `.env` 中的 `PDF_PARSE_BACKEND`。
- `pypdf` 速度快，但对复杂版式、扫描件和表格支持弱。
- `mineru` 解析更完整，但会进行 OCR、版面分析和表格识别，大 PDF 可能需要数分钟。
- MinerU 执行日志会输出到终端，并在文档处理目录生成 `mineru.log`。

## 大模型配置

项目可以不配置大模型直接运行。本地默认会使用启发式商品识别和本地答案生成逻辑。

如需启用 DashScope / Qwen：

```env
ENABLE_EXTERNAL_LLM=true
OPENAI_API_KEY=你的密钥
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_DEFAULT_MODEL=qwen-flash
ITEM_MODEL=qwen-flash
VL_MODEL=qwen3-vl-flash
```

不要把真实密钥提交到 GitHub，`.env` 文件已被忽略。

## BGE-M3 向量模型

默认配置是：

```env
EMBEDDING_MODEL=local-hash
```

这个模式启动快，适合本地演示。若要使用真实 BGE-M3 生成向量，建议在 Python 3.12 环境安装：

```bash
source .venv312/bin/activate
pip install -e ".[bge]"
```

然后修改 `.env`：

```env
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
BGE_M3=BAAI/bge-m3
BGE_M3_PATH=
BGE_DEVICE=cpu
BGE_FP16=false
```

如果你已经把模型下载到本地，可以填写：

```env
BGE_M3_PATH=/你的本地模型路径/bge-m3
```

如果 HuggingFace 下载速度慢，可以用 ModelScope 国内源提前下载：

```bash
source .venv312/bin/activate
python scripts/download_bge_m3.py
```

脚本会输出类似：

```env
BGE_M3_PATH=/path/to/downloaded/bge-m3
```

把输出的 `BGE_M3_PATH` 填入 `.env` 后重启后端即可。

说明：

- BGE-M3 会同时生成 `dense_vector` 和 `sparse_vector`。
- `dense_vector` 用于语义检索，`sparse_vector` 用于关键词匹配。
- 首次使用可能需要下载模型，CPU 推理会比本地模拟向量慢。
- 如果使用 Milvus，请保持 `EMBEDDING_DIM=1024`，并在切换向量维度或模型后清空旧 collection 后重新导入文档。

## API 示例

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

导入文档，轻量 pypdf：

```bash
curl -F "file=@demo.pdf" -F "parse_mode=pypdf" http://127.0.0.1:8000/api/import
```

导入文档，MinerU：

```bash
curl -F "file=@demo.pdf" -F "parse_mode=mineru" http://127.0.0.1:8000/api/import
```

查询任务：

```bash
curl http://127.0.0.1:8000/api/tasks
curl http://127.0.0.1:8000/api/tasks/{task_id}
```

知识库问答：

```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"RS-12 如何测量直流电压？","top_k":5}'
```

## 项目结构

```text
IKB-Agent/
├── ikb_agent/
│   ├── main.py                  # FastAPI 应用装配
│   ├── api/                     # API 路由层
│   ├── services/                # 业务服务层
│   ├── core/                    # 依赖注入与路径工具
│   ├── pipeline/
│   │   ├── import_pipeline.py   # LangGraph 导入图
│   │   ├── state.py             # 图状态定义
│   │   └── nodes/               # 导入节点，每个节点独立文件
│   ├── processor/               # 对齐课件命名的兼容入口
│   ├── schema/                  # 请求/任务 schema
│   ├── utils/                   # Milvus、MinIO、Mongo、LLM 等工具
│   ├── models.py                # Pydantic 数据模型
│   ├── settings.py              # 配置管理
│   ├── storage.py               # JSON / Milvus 混合存储
│   ├── text_utils.py            # 分词、向量化、商品名启发式识别
│   └── static/                  # 前端工作台
├── scripts/
│   ├── check_mineru.py
│   └── test_connections.py
├── tests/
├── docs/
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## 核心代码位置

| 功能 | 文件 |
| --- | --- |
| 导入图编排 | `ikb_agent/pipeline/import_pipeline.py` |
| PDF 解析模式 | `ikb_agent/pipeline/nodes/pdf_to_markdown_node.py` |
| Markdown 加载 | `ikb_agent/pipeline/nodes/markdown_load_node.py` |
| 图片语义化 | `ikb_agent/pipeline/nodes/markdown_image_node.py` |
| 文档切分 | `ikb_agent/pipeline/nodes/document_split_node.py` |
| 商品识别 | `ikb_agent/pipeline/nodes/item_name_recognition_node.py` |
| Embedding | `ikb_agent/pipeline/nodes/embedding_node.py` |
| 向量入库 | `ikb_agent/pipeline/nodes/import_store_node.py` |
| 混合检索 | `ikb_agent/services/query_service.py` |
| 前端页面 | `ikb_agent/static/` |

## 测试

```bash
pip install -e ".[dev,pdf]"
pytest
```

当前测试覆盖：

- 标题层级切分保留上下文。
- 商品名识别结果回填到所有 Chunk。
- 导入任务状态更新。
- 查询时商品名识别不误伤混合检索召回。
- 单次上传 `pypdf / mineru` 解析模式覆盖全局配置。

## 面试讲法

这个项目不是一个简单的聊天页面，而是一套 RAG 文档处理平台。导入侧负责把非结构化文档转成高质量知识数据，经过解析、图文增强、语义切分、实体识别和向量化后入库；查询侧通过商品名和混合检索召回相关 Chunk，再组织可追溯答案。

可以重点讲：

- 为什么复杂 PDF 需要 MinerU，而不是只用普通文本抽取。
- 为什么提供 `pypdf` 和 `mineru` 两种模式：本地演示追求速度，生产导入追求解析质量。
- 为什么按标题层级切分，而不是固定长度硬切。
- 为什么短 Chunk 要按同父标题合并，减少碎片化。
- 为什么商品名要回填到所有 Chunk，方便精确过滤和业务检索。
- 为什么使用 Dense + Sparse 混合检索，兼顾语义相似和关键词命中。
- 为什么用 LangGraph 编排导入链路，方便节点状态管理、失败重试和链路追踪。

## 更多文档

更详细的 Docker 部署、PyCharm 启动、MinerU 安装和连接排查见：

- `docs/DEPLOYMENT.md`
- `docs/ARCHITECTURE.md`
