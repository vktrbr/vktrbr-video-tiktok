import asyncio

import tiktok_topic_parse
from constants import TOPICS


async def main():
    for topic in TOPICS:
        await tiktok_topic_parse.main(topic, 20)


if __name__ == '__main__':
    asyncio.run(main())
