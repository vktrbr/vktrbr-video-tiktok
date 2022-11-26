import asyncio
import json
import logging

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

# Пути к распрашенным данным
PATH_PREVIEWS = './data/previews/'
PATH_VIDEOS = './data/videos/'
PATH_JSON = './data/jsons/'

VIDEO_QUANTITY = 250  # Количество постов, которые нужно скачать
SLEEP_TIME_SEC = 3  # Количество секунд, которое ждем после действия на странице, чтобы капчу не поймать
COOKIES_USER = './data/my_cookies'  # Путь к файлу с куками

with open(COOKIES_USER, 'r') as cookies:
    cookies = dict(list(map(lambda x: x.split('\t')[:2], cookies.readlines())))

# Название блока в html страницы, в котором лежит инфа по видео
CLASS_NAME_OF_POST_BLOCK = "tiktok-1soki6-DivItemContainerForSearch e19c29qe9"

# Класс, в котором лежат лайки
CLASS_NAME_OF_LIKES_BLOCK = "tiktok-wxn977-StrongText edu4zum2"

# Класс, в котором лежит описание видео
CLASS_NAME_OF_DESCRIPTION_BLOCK = "tiktok-5dmltr-DivContainer ejg0rhn0"

# Класс, в котором лежит ник автора
CLASS_NAME_OF_AUTHOR_NICKNAME_BLOCK = "tiktok-1r8gltq-SpanUniqueId e17fzhrb1"

# Путь к кнопке "Показать еще"
XPATH_BUTTON = '//button[@class="tiktok-154bc22-ButtonMore e17vxm6m1"]'


async def setup_driver_tiktok(_cookies: dict) -> webdriver:
    """
    Запускает драйвер для тиктока.

    :param _cookies: Куки, которые нужно передать в сафари.
    :return: Драйвер.
    """

    driver = webdriver.Safari()
    # Открываем ТикТок и ждем. Потом подгружаем куки и можем использовать
    driver.get(f'https://www.tiktok.com')
    await asyncio.sleep(SLEEP_TIME_SEC / 2)

    for cookie_name, cookie_value in _cookies.items():
        driver.add_cookie({'name': cookie_name, 'value': cookie_value})

    return driver


async def get_page_by_topic(topic: str, video_quantity: int, driver: webdriver) -> list[str]:
    """
    Идет в тикток, через открытие сафари. Парсит нужное количество "видео". Под каждым видео понимается
    блок с превью, автором, количеством лайков и прочими метаданными.

    :param topic: Тема, по которой идет поиск.
    :param video_quantity: Количество видео, которые нужно скачать.
    :param driver: Драйвер, который нужно использовать.
    :return: Список строк с html с данными из поста.
    """
    print(f'Открываем топик {topic}')

    url = f'https://www.tiktok.com/search?q={topic}'
    driver.get(url)

    await asyncio.sleep(SLEEP_TIME_SEC)

    page_topic = BeautifulSoup(driver.page_source, 'html.parser').find_all(class_=CLASS_NAME_OF_POST_BLOCK)

    # Пока не соберем нужное количество видео, будем скроллить страницу
    cnt_errs = 0

    while len(page_topic) < video_quantity and cnt_errs < 3:
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
        await asyncio.sleep(SLEEP_TIME_SEC)

        try:
            driver.find_element(by=By.XPATH, value=XPATH_BUTTON).click()
            await asyncio.sleep(SLEEP_TIME_SEC)
        except Exception as e:
            cnt_errs += 1
            print(e)

            driver.execute_script("window.scrollTo(0,window.pageYOffset-30)")
            driver.execute_script("window.scrollTo(0,window.pageYOffset+30)")

            await asyncio.sleep(SLEEP_TIME_SEC * 2)

        page_topic = BeautifulSoup(driver.page_source, 'html.parser').find_all(class_=CLASS_NAME_OF_POST_BLOCK)

    return list(map(str, page_topic))[:video_quantity]


async def get_attrs_from_window(html: str) -> dict[str, str]:
    """
    Парсит ссылку на превью и пост, количество просмотров.

    :param html: Строка с html кодом, который нужно распарсить.
    :return: Словарь с данными
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Парсим ссылку на пост
    post_link = soup.find(class_='tiktok-yz6ijl-DivWrapper e1cg0wnj1').find('a').get('href')

    # Парсим ссылку на превью
    preview_link = soup.find(class_='tiktok-1itcwxg-ImgPoster e1yey0rl1').get('src')

    # Парсим количество просмотров
    views = soup.find(class_='tiktok-ws4x78-StrongVideoCount etrd4pu10').text

    return {'post_link': post_link, 'preview_link': preview_link, 'views': views}


async def download_data(link: str, path: str) -> None:
    """
    Скачивает файл по ссылке.

    :param link: Ссылка на файл.
    :param path: Путь, куда нужно сохранить файл.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as resp:
            if resp.status == 200:
                f = await aiofiles.open(path, mode='wb')
                await f.write(await resp.read())
                await f.close()


async def get_info_from_post(post: dict[str], driver: webdriver) -> dict[str, str]:
    """
    Идет в сам пост и парсит лайки, ник юзера, описание видео и скачивает само видео.

    :param post: Ссылки на пост и превью.
    :param driver: Драйвер сафари.
    :return: Словарь с данными.
    """
    link = post['post_link']
    print(f'Идем в пост {link}')

    # Преходим в ТикТок и ждем, пока загрузится страница;
    driver.get(link)
    await asyncio.sleep(SLEEP_TIME_SEC * 3)

    # Парсим всю страницу. В ней найдем ссылку на видео, лайки, описание
    page = BeautifulSoup(driver.page_source, 'html.parser')

    # Парсим лайки
    likes = page.find(class_=CLASS_NAME_OF_LIKES_BLOCK).text

    # Парсим описание
    description = page.find(class_=CLASS_NAME_OF_DESCRIPTION_BLOCK).text

    # Парсим ник юзера
    user_nickname = page.find(class_=CLASS_NAME_OF_AUTHOR_NICKNAME_BLOCK).text

    # Парсим ссылку на видео
    video_link = page.find(mediatype='video').get('src')

    # Скачиваем превью
    preview_path = f'./{PATH_PREVIEWS}/{link.split("/")[-1]}.jpg'
    await download_data(post['preview_link'], preview_path)

    # Скачиваем видео
    video_path = f'{PATH_VIDEOS}/video-{link.split("/")[-1]}.mp4'
    await download_data(video_link, video_path)

    return {'likes': likes, 'description': description, 'user_nickname': user_nickname,
            'video_path': video_path, 'preview_path': preview_path}


async def main(topic: str = 'datascience'):
    safari_driver = await setup_driver_tiktok(cookies)
    full_video_window = await get_page_by_topic(topic, VIDEO_QUANTITY, driver=safari_driver)

    async with asyncio.TaskGroup() as tg:
        posts = []
        for post in full_video_window:
            posts.append(await tg.create_task(get_attrs_from_window(post)))

    # Пройдем по всем постам параллельно и соберем информацию. Используем gather, чтобы не ждать,
    # пока все посты обработаются
    async with asyncio.TaskGroup() as _:
        post_info = []
        for group_index in range(0, len(posts), 10):
            sub_posts = posts[group_index:group_index + 10]
            post_info.extend(await asyncio.gather(*[get_info_from_post(post, safari_driver) for post in sub_posts]))

    posts = [dict(post, **info) for post, info in zip(posts, post_info)]
    json.dump(posts, open(f'{PATH_JSON}/posts-{topic}.json', 'w'), indent=4)
    safari_driver.close()

    return posts


if __name__ == '__main__':
    import time

    start = time.time()
    print(asyncio.run(main()))
    print(time.time() - start)
