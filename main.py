import os.path
import sys
import sqlite3
import eyed3
from time import sleep

import requests
from pyncm import DumpSessionAsString, LoadSessionFromString, GetCurrentSession, SetCurrentSession
from pyncm.apis import login, playlist, track


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
        print("登录成功")
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
        print(f"SKIP: {track_id}")
    else:
        print(f"ADD: {track_id}")
        cursor.execute("INSERT INTO songs VALUES (?, ?, ?)", (track_id, at, 0))


def download_song(track_id, info, audio):
    audio_url = audio["url"]
    # TODO: 校验 md5
    # md5_hash = audio["md5"]
    title = info["name"]
    album = info["al"]["name"]
    if not album:
        print(f"[跳过云盘]: {title}")
        return
    if audio_url is None:
        print(f"[无版权]: {title}-<{album}> {track_id}")
        return
    authors = []
    filename = f"{title}.mp3".replace("/", "_")
    for author in info["ar"]:
        authors.append(author["name"])
    # cover = None
    try:
        cover = requests.get(info["al"]["picUrl"]).content
    except Exception as e:
        print("封面下载失败")
        return
    print(f"[下载]: {title}-<{album}>")
    try:
        lyrics = track.GetTrackLyrics(track_id)["lrc"]["lyric"]
    except Exception as e:
        if e is not KeyError:
            print("下载歌词失败")
            return
        else:
            lyrics = None
    # TODO: 文件重名判定
    # TODO: 字符过滤
    try:
        resp = requests.get(audio_url)
        if not resp.ok:
            print(f"[ERROR]: {resp.status_code} {audio_url}")
            return
        mp3 = resp.content
        with open(filename, "wb+") as file:
            file.write(mp3)
    except Exception as e:
        print("歌曲下载失败")
        print(e)
        return
    song = eyed3.load(filename)
    if song is None:
        print(f"[ERROR]: {filename} failed to open")
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
    sleep(20)


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


def print_help():
    help_massage = """网易云歌单下载

Usage: 
python main.py fetch [TRACK_ID]             更新本地歌曲数据库 
python main.py download [TRACK_ID]          下载数据库内的歌曲
    """
    print(help_massage)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        if not os.path.exists("login.secret"):
            print("需要登录")
            phone_login()
        # TODO: 登录状态确认
        with open("login.secret") as secret:
            print("已登录")
            SetCurrentSession(LoadSessionFromString(secret.read()))
        track_id = sys.argv[2]
        if not os.path.exists(f"{track_id}.db"):
            db = sqlite3.connect(f"{track_id}.db")
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE "songs" ("id"INTEGER NOT NULL UNIQUE,"add_date"INTEGER,
            "downloaded"INTEGER,PRIMARY KEY("id"))""")
        else:
            db = sqlite3.connect(f"{track_id}.db")
            cursor = db.cursor()
        if sys.argv[1] == "fetch":
            get_all_tracks(track_id)
        elif sys.argv[1] == "download":
            download_all()
        db.close()
    else:
        print_help()
        exit(0)

