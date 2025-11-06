import asyncio
from agent import Agent
from browser import Browser


async def run():
    agent = Agent()
    browser = Browser(agent=agent)
    await browser.run()


if __name__ == "__main__":
    asyncio.run(run())
