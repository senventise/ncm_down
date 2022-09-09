# 网易云歌单下载
下载网易云歌单内所有歌曲，包括VIP歌曲（需要VIP账号），包括作者、专辑、封面、歌词（不包含翻译）等信息。

## 使用
使用时需要登录，目前只支持验证码登录，密码登录疑似有问题。    
需要歌单的`track id`，可以在歌单url中找到。  
**下载中可能报错，疑似是风控，过一会再下载就会恢复正常**，所以采用了先将歌曲id写入数据库、再下载的模式。
```shell
git clone https://github.com/senventise/ncm_down.git
cd ncm_down/
# 下载所有歌曲 id
python main.py fetch [TRACK_ID]
# 根据本地数据库下载所有歌曲，已下载的会自动跳过
python main.py download [TRACK_ID]
```
## 致谢
感谢[pyncm](https://github.com/mos9527/pyncm)。