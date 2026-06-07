"""链接导入器 - 处理用户手动提供的 URL 列表"""

from src.collector.web_scraper import WebScraper


class LinkImporter:
    """导入用户提供的文章/网页链接"""

    def __init__(self):
        self.scraper = WebScraper()

    async def import_links(self, urls: list[str]) -> list[dict]:
        """批量导入链接并抓取内容"""
        raw_results = await self.scraper.scrape_urls(urls)
        results = []
        for item in raw_results:
            if item.get("content") and item["content"].strip():
                results.append({**item, "source_type": "link"})
            else:
                results.append({**item, "source_type": "link", "content": "[无法访问或内容为空]"})
        return results
