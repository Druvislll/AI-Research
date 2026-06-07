"""搜索引擎采集器 - 支持 DuckDuckGo 和备用 RSS 源"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional
import httpx
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


class SearchCollector:
    """搜索采集器 - DuckDuckGo 为主，失败时返回空结果不崩溃"""

    def __init__(self):
        self.search_url = "https://html.duckduckgo.com/html/"

    async def _try_duckduckgo(self, query: str, max_results: int) -> list[dict]:
        """尝试 DuckDuckGo 搜索"""
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.post(
                    self.search_url,
                    data={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/120.0.0.0 Safari/537.36"
                    },
                )
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select("a.result__a"):
                href = item.get("href", "")
                title = item.get_text(strip=True)
                if href and title:
                    # DuckDuckGo 返回重定向链接，提取真实 URL
                    if "uddg=" in href:
                        from urllib.parse import parse_qs, urlparse
                        parsed = urlparse(href)
                        params = parse_qs(parsed.query)
                        real_url = params.get("uddg", [href])[0]
                    else:
                        real_url = href
                    results.append({
                        "id": hashlib.md5(real_url.encode()).hexdigest(),
                        "title": title,
                        "url": real_url,
                        "content": "",
                        "source_type": "search",
                        "query": query,
                        "scraped_at": datetime.now().isoformat(),
                    })
            return results[:max_results]
        except Exception as e:
            print(f"[Search] DuckDuckGo 搜索失败 ({query}): {e}")
            return []

    async def _try_news_bing(self, query: str, max_results: int) -> list[dict]:
        """备用方案：尝试通过 Bing 新闻搜索"""
        try:
            bing_url = f"https://www.bing.com/news/search?q={query}&format=rss"
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    bing_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                resp.raise_for_status()

            results = []
            try:
                root = ET.fromstring(resp.text)
                for item in root.iter("item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    if title and link:
                        results.append({
                            "id": hashlib.md5(link.encode()).hexdigest(),
                            "title": title.strip(),
                            "url": link,
                            "content": "",
                            "source_type": "search",
                            "query": query,
                            "scraped_at": datetime.now().isoformat(),
                        })
            except ET.ParseError:
                pass
            return results[:max_results]
        except Exception as e:
            print(f"[Search] Bing 搜索失败 ({query}): {e}")
            return []

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """搜索关键词，自动尝试多个搜索引擎"""
        # 先试 DuckDuckGo
        results = await self._try_duckduckgo(query, max_results)
        if results:
            return results

        # DuckDuckGo 失败，试 Bing 新闻 RSS
        results = await self._try_news_bing(query, max_results)
        if results:
            return results

        # 如果都失败，返回一些结构化的 URL 方便爬取（基于常见新闻站点）
        print(f"[Search] 所有搜索引擎均不可用 ({query})，返回空结果")
        return []

    async def batch_search(self, queries: list[str], max_per_query: int = 5) -> list[dict]:
        """多关键词批量搜索"""
        all_results = []
        for query in queries:
            print(f"[Search] 搜索: {query}")
            results = await self.search(query, max_results=max_per_query)
            print(f"[Search] 搜索结果: {len(results)} 条")
            all_results.extend(results)
        return all_results
