# BiliCache2MP4
哔哩哔哩BiliBili视频缓存的*.m4s文件批量转换为.mp4文件工具。支持同时将弹幕转换，支持每个视频組一个文件夹

安卓内部儲存地址：`Android\data\tv.danmaku.bili\download`

## 下载
## Windows(二进制文件)
https://github.com/kaixinol/BiliCache2MP4/releases/
## 类Unix系统
需要先行安裝`ffmpeg`，保證在環境變量裏。
```bash
pip install loguru
curl -O -L https://github.com/m13253/danmaku2ass/raw/master/danmaku2ass.py
curl -O -L https://github.com/kaixinol/BiliCache2MP4/raw/refs/heads/main/converter.py
python converter.py 缓存文件夹 -o 释放文件夹 -danmaku -folder
```
## Usage
```
usage: converter.exe [-h] [-f FFMPEG] [-folder] [-danmaku] [-o OUTPUT] [-t THREAD] FILE

positional arguments:
  FILE                  b站缓存文件文件夹

options:
  -h, --help            show this help message and exit
  -f FFMPEG, --ffmpeg FFMPEG
                        FFmpeg的路径，默认为当前目录
  -folder               是否每一个视频一个文件夹
  -danmaku              是否转换.xml到弹幕文件.aas
  -o OUTPUT, --output OUTPUT
                        释放的位置，默认为本脚本所在目录
  -t THREAD, --thread THREAD
                        多线程数，默认为cpu当前核数
```
