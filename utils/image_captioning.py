"""
Utility to detect images in Hugging Face model-card markdown,
caption them with Google Gemini, and inject the captions inline
so that a downstream text-only LLM can "see" evaluation results
that are only present in images.
"""

import asyncio
import mimetypes
import os
import re
from dataclasses import dataclass

import httpx
from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash"

CAPTION_PROMPT = (
    "Describe this image in detail. If it contains benchmark results, "
    "evaluation scores, leaderboard data, or comparison tables, extract "
    "ALL model names, benchmark names, and numerical scores exactly as shown."
)

MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HTML_IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*/?>", re.IGNORECASE)


@dataclass
class ImageRef:
    original_text: str
    src: str
    alt_text: str


def extract_image_references(markdown: str) -> list[ImageRef]:
    """Find all image references in *markdown* (both ``![]()`` and ``<img>`` tags).

    SVG files are skipped since they are typically logos, not evaluation data.
    """
    refs: list[ImageRef] = []
    seen_srcs: set[str] = set()

    for m in MARKDOWN_IMAGE_RE.finditer(markdown):
        alt, src = m.group(1), m.group(2)
        if src.lower().endswith(".svg") or src in seen_srcs:
            continue
        seen_srcs.add(src)
        refs.append(ImageRef(original_text=m.group(0), src=src, alt_text=alt))

    for m in HTML_IMG_RE.finditer(markdown):
        src = m.group(1)
        if src.lower().endswith(".svg") or src in seen_srcs:
            continue
        seen_srcs.add(src)
        refs.append(ImageRef(original_text=m.group(0), src=src, alt_text=""))

    return refs


def resolve_image_url(src: str, repo_id: str) -> str:
    """Turn a relative image path into a full Hugging Face ``resolve`` URL."""
    if src.startswith(("http://", "https://")):
        return src
    src = src.lstrip("./")
    return f"https://huggingface.co/{repo_id}/resolve/main/{src}"


def _mime_for_url(url: str) -> str:
    mime, _ = mimetypes.guess_type(url)
    return mime or "image/png"


def _get_gemini_api_key() -> str:
    """Return the Gemini API key from the environment.

    Checks ``GEMINI_API_KEY`` first, then falls back to ``GOOGLE_API_KEY``.
    """
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY."
        )
    return key


def caption_image(
    image_bytes: bytes, mime_type: str, gemini_client: genai.Client,
) -> str:
    """Send *image_bytes* to Gemini and return a text caption."""
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            CAPTION_PROMPT,
        ],
    )
    return response.text.strip()


async def _download_and_caption(
    ref: ImageRef,
    repo_id: str,
    http_client: httpx.AsyncClient,
    gemini_client: genai.Client,
    semaphore: asyncio.Semaphore,
) -> tuple[ImageRef, str | None]:
    """Download a single image and caption it.  Returns ``(ref, caption)``."""
    async with semaphore:
        url = resolve_image_url(ref.src, repo_id)
        mime = _mime_for_url(url)
        try:
            resp = await http_client.get(url, follow_redirects=True)
            resp.raise_for_status()
            image_bytes = resp.content
        except Exception as exc:
            print(f"Warning: failed to download image {url}: {exc}")
            return ref, None

        try:
            caption = await asyncio.to_thread(
                caption_image, image_bytes, mime, gemini_client,
            )
        except Exception as exc:
            print(f"Warning: Gemini captioning failed for {url}: {exc}")
            return ref, None

        return ref, caption


async def caption_images_in_markdown(
    markdown: str, repo_id: str, max_concurrent: int = 5
) -> str:
    """Return *markdown* with Gemini-generated captions injected after every image."""
    refs = extract_image_references(markdown)
    if not refs:
        return markdown

    print(f"Found {len(refs)} image(s) to caption in model card")

    gemini_client = genai.Client(api_key=_get_gemini_api_key())
    semaphore = asyncio.Semaphore(max_concurrent)
    async with httpx.AsyncClient(timeout=60) as http_client:
        tasks = [
            _download_and_caption(ref, repo_id, http_client, gemini_client, semaphore)
            for ref in refs
        ]
        results = await asyncio.gather(*tasks)

    for ref, caption in results:
        if caption is None:
            continue
        replacement = f"{ref.original_text}\n\n[Image caption: {caption}]\n"
        markdown = markdown.replace(ref.original_text, replacement, 1)

    return markdown
