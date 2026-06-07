"""报告模板 - 定义结构化报告格式"""

REPORT_TEMPLATE = """# {industry_name}行业研究报告（{report_type}）

**生成时间**: {generated_at}

---

## 一、行业概览
{industry_overview}

## 二、本周核心摘要
本周{industry_name}行业核心变化如下：

{weekly_summary}

## 三、重要事件

### 政策动态
{policy_events}

### 市场动态
{market_events}

### 公司动态
{company_events}

### 技术进展
{tech_events}

### 融资事件
{finance_events}

### 风险提示
{risk_events}

## 四、趋势判断
{trend_analysis}

## 五、重点公司动态
{company_highlights}

## 六、机会与风险

### 市场机会
{opportunities}

### 潜在风险
{risks}

## 七、战略建议
{strategy_advice}

## 八、信息来源
{sources}
"""


def get_empty_section(section_name: str) -> str:
    return f"*（暂无{section_name}相关信息）*"
