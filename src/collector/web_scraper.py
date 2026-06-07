"""网页采集器 - 从新闻网站/行业网站抓取内容"""

import hashlib
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup


class WebScraper:
    """通用网页内容采集器"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def scrape_url(self, url: str) -> Optional[dict]:
        """抓取单个 URL，返回结构化数据"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36"
                }
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 提取标题
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)

            # 移除无用标签
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # 提取正文
            body = soup.find("article") or soup.find("main") or soup.body
            text = body.get_text(separator="\n", strip=True) if body else ""

            # 清洗文本
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines[:200])  # 限制长度

            return {
                "id": hashlib.md5(url.encode()).hexdigest(),
                "title": title or url,
                "url": url,
                "content": text[:50000],  # 限制 50000 字符
                "source_type": "web",
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"id": hashlib.md5(url.encode()).hexdigest(), "title": "", "url": url,
                    "content": "", "source_type": "web", "error": str(e),
                    "scraped_at": datetime.now().isoformat()}

    async def scrape_urls(self, urls: list[str]) -> list[dict]:
        """批量抓取多个 URL"""
        import asyncio
        tasks = [self.scrape_url(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]
