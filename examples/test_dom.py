"""
示例 3: 不用 LLM, 直接测试 DOM 提取
====================================
帮你理解 Agent "看到" 的页面状态长什么样。
不消耗 API 额度, 适合调试。
"""
import asyncio
from browser_use.browser.browser import Browser


async def main():
    browser = Browser(headless=False)  # 显示浏览器窗口
    ctx = await browser.new_context()

    # 打开一个网页
    await ctx.navigate("https://example.com")

    # 提取页面状态
    state = await ctx.get_state()

    # 打印 Agent 看到的内容
    print("=" * 55)
    print("Agent 看到的页面状态:")
    print("=" * 55)
    print(state.to_text())
    print("=" * 55)
    print(f"共 {len(state.elements)} 个可交互元素")

    await ctx.close()
    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
