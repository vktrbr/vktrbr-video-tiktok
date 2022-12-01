import json
import os

import torch

from src.parsing.constants import PATH_JSON, TOPICS

i = 0
posts_data = json.load(open(f"{PATH_JSON}/posts-{TOPICS[i]}.json", 'r'))
video_path = posts_data[0]['video_path']


def convert_number(num: str) -> int:
    """
    Убирает суффиксы К и М из чисел

    :param num: число, которое нужно преобразовать;
    :return: преобразованное число
    """
    if 'K' in num:
        return int(float(num[:-1]) * 1000)
    elif 'M' in num:
        return int(float(num[:-1]) * 1000000)
    else:
        return int(num)


def save_video_to_torch(in_path: str = '../../data/jsons', out_path: str = '../../data/torch') -> None:
    """
    Сохраняет видео, превью, лайки, просмотры, аудио из видео в торч тензоры в одну и папок train / test

    :param in_path: путь к папке с json, в которых лежит вся информация об обучающей выборке.
    :param out_path: путь к папке, в которую будут сохранены торч тензоры;
    """
    d = []
    for json_file in os.listdir(in_path):
        if json_file.endswith('.json'):
            posts_data = json.load(open(f"{in_path}/{json_file}", 'r'))
            for post in posts_data:
                # fps, video_tensor = ffmpegio.video.read(post['video_path'])
                # sample_rate, audio_tensor = ffmpegio.audio.read(post['video_path'])

                # preview = ffmpegio.image.read(post['preview_path'])
                if 'likes' in post and 'views' in post:
                    likes = convert_number(post['likes'])
                    views = convert_number(post['views'])

                d.append(likes / views)
                # video_tensor = torch.tensor(video_tensor).permute(0, 3, 1, 2)[::3]
                # audio_tensor = torch.tensor(audio_tensor)[:, 0]
                # preview = torch.tensor(preview).permute(2, 0, 1)
                likes = torch.tensor([likes])
                views = torch.tensor([views])

                directory = 'train' if torch.rand(1) < 25 else 'test'

                # torch.save((
                #     video_tensor,
                #     audio_tensor,
                #     preview,
                #     likes,
                #     views
                # ), f"{out_path}/{directory}/{post['video_path'].split('/')[-1].split('.')[0]}.pt")
                #
                # print(video_tensor.shape, audio_tensor.shape, preview.shape, likes.shape, views.shape)
                print(likes, views, likes / views)

    return d

import plotly.express as px



if __name__ == '__main__':
    d = save_video_to_torch()
    px.histogram(d).show()