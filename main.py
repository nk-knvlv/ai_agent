import asyncio
from agent import Agent
from browser import Browser


async def run():
    browser = Browser()
    agent = Agent(browser)
    await agent.wake_up()


if __name__ == "__main__":
    asyncio.run(run())
