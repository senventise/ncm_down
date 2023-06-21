import os.path
import sqlite3
from time import sleep
import argparse

import eyed3
import requests
from pyncm import DumpSessionAsString, LoadSessionFromString, GetCurrentSession, SetCurrentSession
from pyncm.apis import login, playlist, track
from rich import print
from rich import status


def phone_login():
    """
    手机号登录
    """
    phone = input("手机: ").strip()
    login.SetSendRegisterVerifcationCodeViaCellphone(phone)
    captcha = input("验证码: ").strip()
    # 密码登录疑似失效
    # password = getpass("密码: ")
    result = login.LoginViaCellphone(phone, captcha=captcha)
    if result:
        print("[bold green]登录成功[/bold green]")
    with open("login.secret", "w+") as secret_file:
        print("登录状态已保存")
        secret_file.write(DumpSessionAsString(GetCurrentSession()))


def get_all_tracks(playlist_id):
    """
    抓取所有歌曲信息，写入数据库
    :param playlist_id: 歌单id
    """
    pl = playlist.GetPlaylistInfo(playlist_id)["playlist"]
    track_ids = pl["trackIds"]
    for _track in track_ids:
        db_insert(_track["id"], _track["at"])
    db.commit()


def db_insert(track_id, at):
    """
    将歌曲id插入数据库
    :param track_id: 歌曲 id
    :param at: 歌曲加入歌单的时间
    """
    cursor.execute('SELECT * FROM songs WHERE (id=?)', (track_id,))
    entry = cursor.fetchone()
    if entry is not None:
        print(f"[italic]跳过: {track_id}[/italic]")
    else:
        print(f"添加: {track_id}")
        cursor.execute("INSERT INTO songs VALUES (?, ?, ?)", (track_id, at, 0))


def download_song(track_id, info, audio):
    audio_url = audio["url"]
    # TODO: 校验 md5
    # md5_hash = audio["md5"]
    title = info["name"]
    album = info["al"]["name"]
    if not album:
        print(f"[italic]跳过云盘: {title}[/italic]")
        return
    if audio_url is None:
        print(f"[italic]无版权: {title}-<{album}> {track_id}[/italic]")
        return
    authors = []
    filename = f"{title}.mp3".replace("/", "_")
    for author in info["ar"]:
        authors.append(author["name"])
    # cover = None
    try:
        cover = requests.get(info["al"]["picUrl"]).content
    except Exception as e:
        print("[bold red]封面下载失败[/bold red]")
        return
    print(f"[bold green]正在下载：{title}-<{album}>[/bold green]")
    try:
        lyrics = track.GetTrackLyrics(track_id)["lrc"]["lyric"]
    except Exception as e:
        if e is not KeyError:
            print("[bold red]下载歌词失败[/bold red]")
            return
        lyrics = None
    # TODO: 文件重名判定
    # TODO: 字符过滤
    try:
        resp = requests.get(audio_url)
        if not resp.ok:
            print(f"[bold red]出错：{resp.status_code} {audio_url}[/bold red]")
            return
        mp3 = resp.content
        with open(filename, "wb+") as file:
            file.write(mp3)
    except Exception as e:
        print("[bold red]歌曲下载失败[/bold red]")
        print(e)
        return
    song = eyed3.load(filename)
    if song is None:
        print(f"[bold red]无法打开：{filename}[/bold red]")
        return
    if song.tag is None:
        song.initTag()
    song.tag.title = title
    song.tag.artist = " & ".join(authors).strip()
    song.tag.album = album
    song.tag.images.set(3, cover, "image/jpeg")
    if lyrics:
        song.tag.lyrics.set(lyrics)
    song.tag.save(encoding="utf-8")
    cursor.execute("UPDATE songs SET downloaded=1 WHERE id=(?)", (track_id,))
    db.commit()
    with status.Status('睡眠中...', spinner='point'):
        sleep(args.sleep)


def download_all():
    """
    从数据库中读取并下载所有歌曲
    """
    tracks = []
    for row in cursor.execute("SELECT * FROM songs WHERE downloaded=0 ORDER BY add_date DESC"):
        tracks.append(row[0])
    chunks = [tracks[x:x + 100] for x in range(0, len(tracks), 100)]
    for chunk in chunks:
        # chunk: list of track_id
        infos = track.GetTrackDetail(chunk)["songs"]
        audios = track.GetTrackAudio(chunk, 128000)["data"]
        for track_id in chunk:
            info = next(filter(lambda x: x["id"] == track_id, infos))
            audio = next(filter(lambda x: x["id"] == track_id, audios))
            download_song(track_id, info, audio)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='python main.py', description='网易云音乐歌单下载')

    parser.add_argument('action', choices=['fetch', 'download'], help='抓取歌单信息/下载')
    parser.add_argument('--sleep', type=int, help='每首歌下载完毕后的睡眠时间，不建议设为很低的值。', default=15)
    parser.add_argument('track_id', type=int, help='歌单的ID，可在歌单URL找到。')

    args = parser.parse_args()

    if not os.path.exists("login.secret"):
        print("[bold red]需要登录[/bold red]")
        phone_login()
    # TODO: 登录状态确认
    with open("login.secret") as secret:
        print("[bold green]已登录[/bold green]")
        SetCurrentSession(LoadSessionFromString(secret.read()))

    if not os.path.exists(f"{args.track_id}.db"):
        db = sqlite3.connect(f"{args.track_id}.db")
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE "songs" ("id"INTEGER NOT NULL UNIQUE,"add_date"INTEGER,
        "downloaded"INTEGER,PRIMARY KEY("id"))""")
    else:
        db = sqlite3.connect(f"{args.track_id}.db")
        cursor = db.cursor()

    if args.action == "fetch":
        get_all_tracks(args.track_id)
    elif args.action == "download":
        download_all()

    db.close()
