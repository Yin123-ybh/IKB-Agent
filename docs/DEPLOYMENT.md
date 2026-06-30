# Local Test and Middleware Deployment

这份说明对应课件 1「项目全景」和课件 2「环境配置&服务部署指南」。

## 要不要用 Docker

要分两层看：

- 本地演示和面试讲解：不强制需要 Docker。直接安装 `requirements.txt`，运行 FastAPI，就能上传 Markdown/PDF、执行 LangGraph 导入链路、切分、商品识别、Embedding、JSON 入库和检索问答。
- 接近课程生产环境：需要 Docker 部署中间件。课件里的 Milvus、Etcd、MinIO、Attu、MongoDB 都适合用 `docker compose` 启动；应用代码本身仍然可以在 PyCharm 里本地运行。

也就是说，Docker 主要负责数据基础设施，不是必须把 Python 项目也放进 Docker 才能开发。

## 课件组件和本仓库对应关系

| 课件组件 | 本仓库实现 | 本地可测状态 |
| --- | --- | --- |
| FastAPI / Uvicorn | `ikb_agent/main.py`, `ikb_agent/api/*` | 默认可测 |
| LangGraph 导入流程 | `ikb_agent/pipeline/import_pipeline.py` | 默认可测 |
| 导入节点 | `ikb_agent/pipeline/nodes/*` | 默认可测 |
| Schema | `ikb_agent/schema/*` | 默认可测 |
| Service | `ikb_agent/services/*` | 默认可测 |
| MinerU | `PdfToMarkdownNode` 支持 `PDF_PARSE_BACKEND=mineru` 调用 CLI | 装 MinerU 后可测 |
| Qwen3-VL-Flash | `MarkdownImageNode` 可读取图片并调用 VL 模型生成语义描述 | 配置密钥后可测 |
| BGE-M3 | `utils/embedding_utils.py` 本地向量替代 | 默认可测 |
| Milvus | `utils/milvus_utils.py`, `docker-compose.yml` | 装中间件依赖后可测 |
| MinIO | `utils/minio_utils.py`, `docker-compose.yml` | 装中间件依赖后可测 |
| MongoDB | `utils/mongo_history_utils.py`, `docker-compose.yml` | 装中间件依赖后可测 |
| Attu | `docker-compose.yml` | Docker 启动后访问 |

## PyCharm 本地启动

1. 用 PyCharm 打开项目根目录 `IKB-Agent`。
2. 选择 Python 3.10+ 解释器。
3. 安装基础依赖：

```bash
pip install -r requirements.txt
```

4. 如果需要轻量读取 PDF 文本，再装：

```bash
pip install -e ".[pdf]"
```

课件完整版使用 MinerU。MinerU 通常需要 Python 3.10-3.13 环境；如果你当前解释器是 Python 3.14，建议新建 Python 3.12 虚拟环境后安装：

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
pip install -e ".[pdf,middleware,mineru]"
```

然后在 `.env` 中启用：

```env
PDF_PARSE_BACKEND=mineru
MINERU_CLI=mineru
MINERU_METHOD=auto
MINERU_BACKEND=pipeline
MINERU_SOURCE=local
MINERU_FORMULA=false
MINERU_TABLE=true
```

课件第四章的命令是 `mineru -p <pdf_path> -o <output_dir> --source local`，核心目的是使用本地模型，避免每次解析都重新下载。新版 MinerU 3.x 的命令帮助里可能已经没有 `--source` 参数，本项目会自动检测：支持时才传 `--source local`，不支持时跳过，避免命令失败。

速度说明：

- `PDF_PARSE_BACKEND=pypdf` 是轻量文本抽取，所以同一个 PDF 会很快，但表格、图片、复杂版式还原能力弱。
- `PDF_PARSE_BACKEND=mineru` 会加载版面分析、OCR、表格等模型，第一次运行还可能下载模型，因此明显更慢。
- 文本型 PDF 可以把 `MINERU_METHOD=txt` 改快一些；扫描件或复杂图片 PDF 建议继续用 `auto` 或 `ocr`。
- 执行时终端会输出 `[MinerU] ...` 实时日志，并在文档处理目录生成 `mineru.log`，方便判断慢在下载模型、OCR 还是表格识别。

前端上传时也可以为单个文件选择解析模式。接口参数为 multipart form 字段：

```bash
curl -F "file=@demo.pdf" -F "parse_mode=pypdf" http://127.0.0.1:8000/api/import
curl -F "file=@demo.pdf" -F "parse_mode=mineru" http://127.0.0.1:8000/api/import
```

这个单次参数优先级高于 `.env` 中的 `PDF_PARSE_BACKEND`，因此可以在同一个服务里分别测试轻量版和 MinerU 版。

检查 MinerU 是否就绪：

```bash
python scripts/check_mineru.py
```

### 启用真实 BGE-M3 向量

默认 `EMBEDDING_MODEL=local-hash` 是本地轻量模拟向量。若需要课件中的真实 BGE-M3：

```bash
source .venv312/bin/activate
pip install -e ".[bge]"
```

然后在 `.env` 中配置：

```env
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
BGE_M3=BAAI/bge-m3
BGE_M3_PATH=
BGE_DEVICE=cpu
BGE_FP16=false
```

如果你本地已经有 BGE-M3 模型目录，优先填写 `BGE_M3_PATH`，可以避免每次从远程仓库解析模型。切换模型后，建议重新导入文档；如果使用 Milvus 且 collection 已存在，必要时先删除旧 collection，避免旧向量和新向量混用。

如果 HuggingFace 下载卡住，可以改用 ModelScope 国内源下载：

```bash
source .venv312/bin/activate
python scripts/download_bge_m3.py
```

脚本执行完成后会输出：

```env
BGE_M3_PATH=/path/to/downloaded/bge-m3
```

将这行写入 `.env`，重启后端后项目会直接从本地路径加载 BGE-M3。

如果 MinerU CLI 名称是旧版 `magic-pdf`，改成：

```env
MINERU_CLI=magic-pdf
```

5. 复制环境变量文件：

```bash
cp .env.example .env
```

6. 启动后端：

```bash
uvicorn ikb_agent.main:app --reload --host 127.0.0.1 --port 8000
```

7. 浏览器打开：

```text
http://127.0.0.1:8000
```

可以先点击页面里的「导入示例文档」，然后问：

```text
RS-12 如何测量直流电压？
```

## API 自测

```bash
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/demo-import
curl http://127.0.0.1:8000/api/tasks
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"RS-12 如何测量直流电压？","top_k":5}'
```

## 启动中间件

如果你的电脑已经安装 Docker Desktop：

```bash
docker compose up -d
```

服务端口：

| 服务 | 地址 |
| --- | --- |
| Milvus | `localhost:19530` |
| Milvus health | `http://localhost:9091/healthz` |
| MinIO API | `localhost:9000` |
| MinIO Console | `http://localhost:9001` |
| Attu | `http://localhost:7001` |
| MongoDB | `mongodb://localhost:27017` |

MinIO 默认账号密码：

```text
minioadmin / minioadmin
```

## 测试中间件连接

先安装可选中间件依赖：

```bash
pip install -e ".[middleware]"
```

然后执行：

```bash
python scripts/test_connections.py
```

如果输出 Milvus、MongoDB、MinIO 都是 `[ OK ]`，说明 Docker 中间件已经可以被 Python 项目访问。

如果你的网络无法安装这些包，可以在 PyCharm 的 Python Packages 面板里手动安装：

```text
pymilvus
minio
pymongo
```

## 课件完整版开关

Docker 中间件和大模型都配置好后，`.env` 推荐使用：

```env
STORE_BACKEND=milvus
PDF_PARSE_BACKEND=mineru
MINERU_BACKEND=pipeline
MINERU_FORMULA=false
ENABLE_EXTERNAL_LLM=true
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_DEFAULT_MODEL=qwen-flash
ITEM_MODEL=qwen-flash
VL_MODEL=qwen3-vl-flash
```

这一模式下：

```text
PDF -> MinerU -> Markdown/图片资源 -> Qwen3-VL 图片语义增强
    -> 标题层级切分/递归切分/短片段合并
    -> Qwen 商品识别
    -> Embedding
    -> Milvus 向量入库 + MinIO 原始文件存储 + MongoDB 任务记录
    -> Milvus 检索 + Qwen 生成答案
```

## 面试讲法

可以这样回答：

> 这个项目本地开发时不强制依赖 Docker，因为我做了 JSON Store 和本地 Embedding 的 fallback，方便快速演示完整 RAG 导入链路。接近生产环境时需要用 Docker 部署 Milvus、Etcd、MinIO、MongoDB 和 Attu。Milvus 负责向量集合和索引，MinIO 负责原始文件和图片资源，MongoDB 负责会话历史和任务链路数据，Python 服务仍然可以在 PyCharm 里运行，通过 `.env` 切换连接地址。
