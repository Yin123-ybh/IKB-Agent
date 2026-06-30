from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from .base import BasePipelineNode
from ..state import ImportState
from ...utils.llm_utils import ChatMessage, get_llm_client


class MarkdownImageNode(BasePipelineNode):
    """Add semantic alt text for Markdown images.

    The production version can call Qwen3-VL-Flash and upload image assets to
    MinIO. The local implementation keeps tests offline and deterministic.
    """

    name = "md_image_node"
    _image_re = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")

    def process(self, state: ImportState) -> ImportState:
        content = state.get("md_content", "")
        md_dir = Path(state.get("md_path", "")).parent if state.get("md_path") else Path(".")

        def replace(match: re.Match[str]) -> str:
            alt = match.group("alt").strip()
            path = match.group("path").strip()
            image_name = Path(path).name
            if alt:
                return match.group(0)
            title = self._nearby_heading(content, match.start())
            image_path = self._resolve_image_path(md_dir, path)
            summary = self._summarize_image_reference(title, image_name, image_path)
            return f"![{summary}]({path})"

        state["md_content"] = self._image_re.sub(replace, content)
        return state

    def _summarize_image_reference(self, title: str, image_name: str, image_path: Path | None) -> str:
        fallback = f"{title} related image: {image_name}" if title else f"Document image: {image_name}"
        if not self.settings.enable_external_llm:
            return fallback
        prompt = (
            "你是文档图片语义增强节点。请为图片生成一句适合写入 Markdown alt 的中文语义描述。"
            "如果图片不可见或信息不足，不要编造细节，控制在 60 字以内。\n\n"
            f"附近标题：{title or '无'}\n图片文件名：{image_name}"
        )
        try:
            user_content = prompt
            if image_path and image_path.exists():
                user_content = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": self._image_to_data_url(image_path)}},
                ]
            result = get_llm_client(self.settings).chat(
                [
                    ChatMessage(role="system", content="你负责生成简短、克制的图片语义描述。"),
                    ChatMessage(role="user", content=user_content),
                ],
                model=self.settings.vl_model,
                timeout=30,
            ).strip()
        except Exception:
            return fallback
        return result[:80] or fallback

    @staticmethod
    def _resolve_image_path(md_dir: Path, image_ref: str) -> Path | None:
        if image_ref.startswith(("http://", "https://", "data:")):
            return None
        path = Path(image_ref)
        return path if path.is_absolute() else md_dir / path

    @staticmethod
    def _image_to_data_url(image_path: Path) -> str:
        mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
        payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{payload}"

    @staticmethod
    def _nearby_heading(content: str, position: int) -> str:
        before = content[:position].splitlines()
        for line in reversed(before):
            if re.match(r"^\s*#{1,6}\s+", line):
                return line.lstrip("#").strip()
        return ""
