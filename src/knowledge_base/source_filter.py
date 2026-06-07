"""信源筛选器 - 域名评分 + 内容质量过滤"""

from urllib.parse import urlparse
from src.utils.logger import log

# 高信誉域名白名单（知名新闻/行业/财经/科技媒体）
HIGH_TRUST_DOMAINS = {
    "36kr.com", "huxiu.com", "latepost.com", "jiemian.com",
    "thepaper.cn", "yicai.com", "caixin.com", "21jingji.com",
    "china.com.cn", "xinhuanet.com", "people.com.cn", "cctv.com",
    "gov.cn", "mofcom.gov.cn", "ndrc.gov.cn", "miit.gov.cn",
    "edu.cn", "sciencedirect.com", "nature.com", "arxiv.org",
    "bloomberg.com", "reuters.com", "ft.com", "wsj.com",
    "techcrunch.com", "theverge.com", "wired.com",
}

# 低信誉域名黑名单（内容农场/低质聚合站）
LOW_TRUST_DOMAINS = {
    "zhuanlan.zhihu.com",  # 个人专栏质量参差不齐
    "baijiahao.baidu.com",  # 百家号
    "toutiao.com",  # 头条号
    "sohu.com",  # 搜狐号（质量偏低）
    "163.com",  # 网易号
}


def _extract_domain(url: str) -> str:
    """从 URL 中提取主域名"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 移除 www. 前缀
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _score_by_domain(domain: str) -> int:
    """基于域名评分 (-5 ~ +10)"""
    if domain in HIGH_TRUST_DOMAINS:
        return 10
    # 检查子域名是否在白名单内
    for trusted in HIGH_TRUST_DOMAINS:
        if domain.endswith("." + trusted):
            return 10
    # 检查 .gov / .edu 顶级域
    if domain.endswith(".gov.cn") or domain.endswith(".edu.cn"):
        return 10
    if domain.endswith(".gov") or domain.endswith(".edu"):
        return 8
    # 黑名单
    if domain in LOW_TRUST_DOMAINS:
        return -5
    for banned in LOW_TRUST_DOMAINS:
        if domain.endswith("." + banned):
            return -5
    # 普通域名
    return 3


def _score_by_length(content: str) -> int:
    """基于内容长度评分 (0 ~ 10)"""
    length = len(content)
    if length < 100:
        return 0
    elif length < 300:
        return 3
    elif length < 800:
        return 6
    elif length < 2000:
        return 8
    else:
        return 10


def _score_by_quality(content: str, title: str) -> int:
    """基于内容质量评分 ( -5 ~ 5)"""
    if not content:
        return -5

    # 检查标题是否出现在正文中（标题大段重复正文 = 低质量）
    if title and len(title) > 5 and content.count(title) > 3:
        return -3

    # 检查是否有常见低质特征
    low_quality_signals = [
        "广告", "推广", " sponsored", "推荐阅读", "关注我们",
    ]
    for signal in low_quality_signals:
        if signal in content[:200]:
            return -2

    # 有段落分割 = 高质量
    paragraphs = content.count("\n\n")
    if paragraphs >= 3:
        return 5
    elif paragraphs >= 1:
        return 3

    return 0


def score_source(item: dict) -> int:
    """对一条来源进行综合评分 (0 ~ 25)"""
    url = item.get("url", "")
    content = item.get("content", "")
    title = item.get("title", "")
    source_type = item.get("source_type", "")

    domain = _extract_domain(url)
    domain_score = _score_by_domain(domain)
    length_score = _score_by_length(content)
    quality_score = _score_by_quality(content, title)

    # 信源类型加分
    type_bonus = {"document": 5, "link": 3, "web": 2, "search": 0}.get(source_type, 0)

    total = domain_score + length_score + quality_score + type_bonus
    log.debug(f"  评分 {total:2d} | 域名{domain_score:2d} 长度{length_score:2d} "
              f"质量{quality_score:2d} 类型{type_bonus:2d} | {title[:30]}")
    return total


def filter_source(item: dict, min_score: int = 3) -> dict | None:
    """筛选一条来源，低于阈值的丢弃，达标的打上 score 标记"""
    total = score_source(item)
    item["score"] = total
    if total < min_score:
        log.info(f"  丢弃 (评分{total} < {min_score}) | {item.get('title', '')[:30]}")
        return None
    return item
