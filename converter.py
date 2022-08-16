
import os
import json
import re
import argparse
global FFmpeg
global NewFolder
global Danmuku

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--ffmpeg', type=str,
                    default="ffmpeg", help="FFmpeg的路径，默认为当前目录")
parser.add_argument('-folder', action='store_true',
                    default=False, help="是否每一个视频一个文件夹")
parser.add_argument('-danmaku', action='store_true',
                    default=False, help="是否转换.xml到弹幕文件.aas")
parser.add_argument('file', metavar='FILE', help='b站缓存文件文件夹')
parser.add_argument('-s', '--save', type=str,
                    default=os.getcwd()+'\\', help='释放的位置，默认为本脚本根目录')

args = parser.parse_args()


FFmpeg = args.ffmpeg
NewFolder = args.folder
Danmaku = args.danmaku
File = args.file
Save = args.save


def DirFolder(n): return [
    n+'/'+i if not os.path.isdir(os.path.realpath((n+i))) else n+i for i in os.listdir(n)]


def Filter(t): return re.sub('[\\\/:*?"<>|]', " ", t)


def SearchFile(name: str, s: str):
    Filelist = []
    for home, dirs, files in os.walk(name):
        for filename in files:
            if os.path.join(home, filename).find(s) != -1:
                Filelist.append(os.path.join(home, filename))
    return Filelist[0] if len(Filelist) == 1 else Filelist


def ReadJson(n: str):
    try:
        with open(os.path.realpath(n), 'r', encoding='utf-8') as load_f:
            load_dict = json.load(load_f)
        return load_dict
    except:
        return None


def ReadTitle(load_dict: dict):
    if 'part' not in load_dict['page_data']:
        return Filter(load_dict['title'])
    else:
        return Filter(load_dict['page_data']['part'])

def MergeVideo(fn):
  ffmpeg=[]
  for i in DirFolder(fn):
   jsonData=ReadJson(SearchFile(i,'entry.json'))
   if NewFolder:
     fl=Save+'\\'+Filter(jsonData['title'])+'\\'+Filter(ReadTitle(jsonData))
     folder=Save+'\\'+Filter(jsonData['title'])+'\\'
     if not os.path.exists(folder):
      os.mkdir(folder)
     ffmpeg.append('{} -i "{}" -i "{}" -c copy "{}.mp4"'.format(FFmpeg,SearchFile(i,'video.m4s'),SearchFile(i,'audio.m4s'),fl))
     if Danmaku:
       ffmpeg.append('python danmaku2ass.py "{}" -s {}x{} -fn "微软雅黑" -fs 48 -a 0.8 -dm 5 -ds 5 -o "{}"'.format(SearchFile(i,'danmaku.xml'),jsonData['page_data']['width'],jsonData['page_data']['height'],fl+'.ass'))
   else:
     if jsonData['type_tag']=='64':
        fl=Save+'\\'+Filter(ReadTitle(jsonData))
     else:
        fl=Save+'\\'+Filter(jsonData['title'])+'-'+Filter(ReadTitle(jsonData))
     ffmpeg.append('{} -i "{}" -i "{}" -c copy "{}.mp4"'.format(FFmpeg,SearchFile(i,'video.m4s'),SearchFile(i,'audio.m4s'),fl))
     if Danmaku:
       ffmpeg.append('python danmaku2ass.py "{}" -s {}x{} -fn "微软雅黑" -fs 48 -a 0.8 -dm 5 -ds 5 -o "{}"'.format(SearchFile(i,'danmaku.xml'),jsonData['page_data']['width'],jsonData['page_data']['height'],fl+'.ass'))
    
  return ffmpeg
for i in DirFolder(File):
    buffer = MergeVideo(i)
    for ii in buffer:
     os.system(ii)
     