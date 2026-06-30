# IKB-Agent

智能知识库系统（RAG 文档处理平台），面向企业产品手册、维修文档、Markdown 知识库等场景，提供文档导入、语义切分、商品识别、混合检索和问答演示。

这个仓库是一个面试友好的完整工程：默认不依赖 GPU、Milvus、MinIO 或外部大模型也能跑通；生产环境可以把本地 JSON store 替换成 Milvus，把轻量向量化替换成 BGE-M3，把图片描述和商品识别替换成 Qwen / DashScope。

## 功能特性

- PDF / Markdown / TXT 上传导入
- LangGraph 编排导入流程
- 标题层级切分 + 递归切分 + 短片段合并
- 商品名识别与 Chunk 元数据回填
- Dense + Sparse 本地混合检索
- FastAPI 后端接口
- 面试演示用前端页面
- 导入任务状态与执行链路追踪
- 可扩展到 MinerU、Qwen3-VL-Flash、BGE-M3、Milvus、MinIO

## 架构流程

```text
Document Upload
  -> EntryNode
  -> PdfToMarkdownNode / MarkdownLoadNode
  -> MarkdownImageNode
  -> DocumentSplitNode
  -> ItemNameRecognitionNode
  -> EmbeddingNode
  -> ImportStoreNode
  -> Query API
```

查询链路：

```text
User Query
  -> 商品名推断
  -> Dense/Sparse 混合检索
  -> Top-K 证据片段
  -> 可追溯答案
```

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn ikb_agent.main:app --reload
```

如需本地直接抽取 PDF 文本，可额外安装：

```bash
pip install ".[pdf]"
```

生产版本建议接入 MinerU 解析复杂 PDF、表格和图片。

打开：

```text
http://127.0.0.1:8000
```

你可以直接点击「导入示例文档」，然后提问：

```text
RS-12 如何测量直流电压？
```

## API

### 健康检查

```bash
curl http://127.0.0.1:8000/api/health
```

### 导入文档

```bash
curl -F "file=@demo.md" http://127.0.0.1:8000/api/import
```

### 查询导入任务

```bash
curl http://127.0.0.1:8000/api/tasks
curl http://127.0.0.1:8000/api/tasks/{task_id}
```

### 查询知识库

```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"RS-12 如何测量直流电压？","top_k":5}'
```

## 项目结构

```text
IKB-Agent/
├── ikb_agent/
│   ├── main.py                  # FastAPI 入口
│   ├── models.py                # Pydantic 数据模型
│   ├── settings.py              # 配置管理
│   ├── storage.py               # 本地知识库，可替换 Milvus
│   ├── text_utils.py            # 分词、向量化、商品名启发式识别
│   ├── pipeline/
│   │   ├── import_pipeline.py   # LangGraph 导入图
│   │   ├── nodes.py             # 导入节点
│   │   └── state.py             # 图状态定义
│   └── static/                  # 前端演示页面
├── tests/
├── .github/workflows/ci.yml
├── docs/
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 和生产版组件的对应关系

| 当前实现 | 生产替换 |
| --- | --- |
| `PdfToMarkdownNode` 轻量 PDF 文本提取 | MinerU 解析正文、表格、图片 |
| `MarkdownImageNode` 本地图片 alt 增强 | Qwen3-VL-Flash 生成图片语义描述 + MinIO |
| `DocumentSplitNode` 标题切分/递归切分/短片段合并 | 可直接保留 |
| `ItemNameRecognitionNode` 启发式商品识别 | Qwen LLM 商品名/实体抽取 |
| `EmbeddingNode` 本地 token 向量 | BGE-M3 Dense + Sparse 向量 |
| `JsonKnowledgeStore` | Milvus Collection + MinIO 原始资源 |

## 核心面试讲法

这个项目不是简单的聊天机器人，而是完整的 RAG 文档处理平台。导入侧负责把 PDF / Markdown 解析成结构化知识，经过图文内容增强、语义切分、商品名识别和向量化后入库；查询侧通过商品维度过滤和 Dense/Sparse 混合检索召回相关 Chunk，再生成可追溯答案。

重点可以讲：

- 为什么按标题层级切分，而不是固定长度硬切
- 为什么短 Chunk 要同父标题合并
- 为什么商品名要回填到所有 Chunk
- 为什么 Dense + Sparse 混合检索适合企业知识库
- 为什么导入链路要用 LangGraph 编排

## 可选中间件

本地演示不强制依赖中间件。如果你想展示生产部署形态，可以启动：

```bash
docker compose up -d
```

包括 Milvus、Etcd、MinIO、Attu 和 MongoDB。当前代码默认使用本地 JSON store；你可以在 `storage.py` 基础上扩展 Milvus 实现。

## 测试

```bash
pip install ".[dev]"
pytest
```
