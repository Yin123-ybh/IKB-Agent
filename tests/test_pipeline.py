from pathlib import Path

from ikb_agent.pipeline.nodes import DocumentSplitNode, ItemNameRecognitionNode
from ikb_agent.settings import Settings


def test_document_split_keeps_heading_context(tmp_path: Path):
    settings = Settings(data_dir=tmp_path, max_chunk_chars=120, min_chunk_chars=20)
    node = DocumentSplitNode(settings)
    state = {
        "file_title": "RS-12",
        "md_content": "# RS-12\n\n## 直流电压测量\n\n第一步，将旋钮拨到 V= 档。第二步，读取屏幕数值。\n\n## 注意事项\n\n禁止电流档测电压。",
    }

    result = node(state)

    assert result["chunks"]
    assert any("直流电压测量" in chunk["content"] for chunk in result["chunks"])
    assert all(chunk["title"] for chunk in result["chunks"])


def test_item_name_recognition_tags_all_chunks(tmp_path: Path):
    settings = Settings(data_dir=tmp_path)
    node = ItemNameRecognitionNode(settings)
    state = {
        "file_title": "万用表RS-12的使用",
        "chunks": [
            {"content": "# RS-12 数字万用表\n\n产品介绍", "title": "# RS-12 数字万用表"},
            {"content": "## 测量步骤\n\n将旋钮拨到 V= 档", "title": "## 测量步骤"},
        ],
    }

    result = node(state)

    assert "RS-12" in result["item_name"]
    assert all(chunk["item_name"] == result["item_name"] for chunk in result["chunks"])

