# Architecture

## Import Pipeline

IKB-Agent uses LangGraph to keep the import pipeline observable and extensible.

```mermaid
flowchart LR
  A["EntryNode"] --> B{"File Type"}
  B -->|PDF| C["PdfToMarkdownNode"]
  B -->|Markdown/TXT| D["MarkdownLoadNode"]
  C --> D
  D --> E["MarkdownImageNode"]
  E --> F["DocumentSplitNode"]
  F --> G["ItemNameRecognitionNode"]
  G --> H["EmbeddingNode"]
  H --> I["ImportStoreNode"]
```

## State Contract

The pipeline passes a single state object across nodes:

```text
import_file_path
file_title
md_path
md_content
chunks
item_name
trace
task_id
```

Each node reads a small subset and writes its own output. This makes every node independently testable.

## Task Tracking

Every import request creates an `ImportTaskRecord`. The API updates it from
`processing` to `completed` or `failed`, stores progress, and persists the
LangGraph node trace:

```text
entry_node -> markdown_load_node -> md_image_node -> document_split_node
  -> item_name_recognition_node -> bge_embedding_chunks_node -> milvus_import_node
```

The current implementation stores tasks in the local JSON store. In production,
the same record can be moved to Redis, MySQL, or MongoDB.

## Retrieval

The local store implements a simple hybrid score:

```text
score = 0.64 * dense_cosine + 0.36 * sparse_overlap
```

Production systems can replace this with Milvus hybrid search and BGE-M3 vectors while keeping the same chunk schema.
