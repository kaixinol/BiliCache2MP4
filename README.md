# BiliCache2MP4
哔哩哔哩Biliili视频缓存的*.m4s文件批量转换为.mp4文件工具。支持同时将弹幕转换，支持每个视频一个文件夹
## 下载
https://github.com/kaixinol/BiliCache2MP4/releases/
## 运行环境
`.py`:Python 3.8+

`.exe`:无
## Usage
```
usage: convert.py [-h] [-f FFMPEG] [-folder] [-danmaku] [-s SAVE] FILE

positional arguments:
  FILE                  b站缓存文件文件夹

options:
  -h, --help            show this help message and exit
  -f FFMPEG, --ffmpeg FFMPEG
                        FFmpeg的路径，默认为当前目录
  -folder               是否每一个视频一个文件夹
  -danmaku              是否转换.xml到弹幕文件.aas
  -s SAVE, --save SAVE  释放的位置，默认为本脚本根目录
```
