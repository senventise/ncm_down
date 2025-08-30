# 网易云歌单下载
下载网易云歌单内所有歌曲，包括VIP歌曲（需要VIP账号），包括作者、专辑、封面、歌词（不包含翻译）等信息。

## 登录
使用时需要登录，目前只支持使用 Cookie 登录。手机验证码登录存在风控。  
登录网页版[网易云音乐](https://music.163.com/)后，通过控制台-存储-Cookie或插件，复制 `MUSIC_U`的值。  
随后，运行脚本，并输入`MUSIC_U`的**值**，即可登录并保存登录状态。

## 使用
需要歌单的`track id`，可以在歌单url中找到。  
**下载中可能报错，疑似是风控，过一会再下载就会恢复正常**，所以采用了先将歌曲id写入数据库、再下载的模式。
```shell
git clone https://github.com/senventise/ncm_down.git
cd ncm_down/
# 抓取歌单信息
python main.py fetch [TRACK_ID]
# 根据本地数据库下载所有歌曲，已下载的会自动跳过
python main.py download [TRACK_ID]
# 为避免风控每首歌下完后会睡眠一段时间，可更改（不建议很小）
python main.py download [TRACK_ID] --sleep 10
# update 等效于 fetch + download
python main.py download [TRACK_ID]
```

## 致谢
感谢[pyncm](https://github.com/mos9527/pyncm)。