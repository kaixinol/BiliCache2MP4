# BiliCache2MP4
哔哩哔哩Biliili视频缓存的*.m4s文件批量转换为.mp4文件工具。支持同时将弹幕转换，支持每个视频一个文件夹
## 下载
## Windows(二进制文件)
https://github.com/kaixinol/BiliCache2MP4/releases/
## 类Unix系统
```bash

```
下载[danmaku2ass.py](https://github.com/m13253/danmaku2ass/raw/master/danmaku2ass.py)到本程序同一目录
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
