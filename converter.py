from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing
from pathlib import Path
import re
import argparse
import time
from loguru import logger
import subprocess

# 命令行解析
parser = argparse.ArgumentParser()
parser.add_argument(
    "-f", "--ffmpeg", type=str, default="ffmpeg", help="FFmpeg的路径，默认为当前目录"
)
parser.add_argument("-folder", action="store_true", default=False, help="是否每一个视频一个文件夹")
parser.add_argument(
    "-danmaku", action="store_true", default=False, help="是否转换.xml到弹幕文件.aas"
)
parser.add_argument("file", metavar="FILE", help="b站缓存文件文件夹")
parser.add_argument(
    "-s", "--save", type=str, default=Path.cwd(), help="释放的位置，默认为本脚本所在目录"
)
parser.add_argument(
    "-t",
    "--thread",
    type=int,
    default=multiprocessing.cpu_count(),
    help="多线程数，默认为cpu当前核数",
)
args = parser.parse_args()

# 初始化
danmaku2ass = (
    "danmaku2ass.exe" if Path("danmaku2ass.exe").exists() else "python danmaku2ass.py"
)
add_author_msg = False  # 个人的需求，可以在文件夹下方生成Author.txt，方便查看原作者
args.file = Path(args.file)
args.save = Path(args.save)
if not Path(args.ffmpeg).exists():
    parser.error("ffmpeg 不存在！")
args.ffmpeg += " -hide_banner -loglevel error"


# 利用os.walk仅查找目录，返回列表
def dir_folder(n):
    return [n / i if not (n / i).is_dir() else n / i for i in Path(n).iterdir()]


# 标题中的非法字符过滤
def illegal_filter(t):
    return re.sub(r'[\/:"*?<>|]', " ", t)


# 搜索文件
def search_file(name: str, s: str):
    file_list = []
    for path in Path(name).rglob("*"):
        if s in path.name:
            file_list.append(path)
    return file_list[0] if len(file_list) == 1 else file_list


def read_json(n: str):
    try:
        with open(Path(n), "r", encoding="utf-8") as load_f:
            load_dict = json.load(load_f)
        return load_dict
    except:
        return None


# 有的json没有part，只有title
def read_title(load_dict: dict):
    if "part" not in load_dict["page_data"]:
        return illegal_filter(load_dict["title"])
    else:
        return illegal_filter(load_dict["page_data"]["part"])


# 生成指令list
def merge_video(fn):
    cmd = []
    for i in dir_folder(fn):
        json_data = read_json(search_file(i, "entry.json"))
        if args.folder:
            mp4 = (
                args.save
                / illegal_filter(json_data["title"])
                / (illegal_filter(read_title(json_data) + ".mp4"))
            )
            ass = (
                args.save
                / illegal_filter(json_data["title"])
                / (illegal_filter(read_title(json_data) + ".ass"))
            )
            folder = args.save / illegal_filter(json_data["title"])
            if not folder.exists():
                folder.mkdir(parents=True)
            if not search_file(i, "audio.m4s"):
                cmd.append(f'{args.ffmpeg} -i "{search_file(i,"video.m4s")}" "{mp4}"')
            else:
                cmd.append(
                    f'{args.ffmpeg} -i "{search_file(i,"video.m4s")}" -i "{search_file(i,"audio.m4s")}" -c copy "{mp4}"'
                )
            if add_author_msg:
                with open(folder / "author.txt", "w+") as f:
                    f.write(
                        f"{json_data['owner_name']}\n{json_data['owner_id']}\n{json_data['bvid']}\n{json_data.get('owner_avatar', '')}"
                    )
            if args.danmaku:
                if not search_file(i, "danmaku.xml"):
                    return cmd
                cmd.append(
                    f'{danmaku2ass} "{search_file(i,"danmaku.xml")}" -s {json_data["page_data"]["width"]}x{json_data["page_data"]["height"]} -fn "微软雅黑" -fs 48 -a 0.8 -dm 5 -ds 5 -o "{ass}"'
                )
        else:
            if json_data["type_tag"] == "64":
                mp4 = args.save / (illegal_filter(read_title(json_data)) + ".mp4")
                ass = args.save / (illegal_filter(read_title(json_data)) + ".ass")
            else:
                mp4 = args.save / (
                    illegal_filter(json_data["title"])
                    + "-"
                    + (illegal_filter(read_title(json_data)) + ".mp4")
                )
                ass = args.save / (
                    illegal_filter(json_data["title"])
                    + "-"
                    + (illegal_filter(read_title(json_data)) + ".ass")
                )
            if not search_file(i, "audio.m4s"):
                cmd.append(
                    f'{args.ffmpeg} -i "{search_file(i,"video.m4s")}" "{mp4}"'
                )
            else:
                cmd.append(
                    f'{args.ffmpeg} -i "{search_file(i,"video.m4s")}" -i "{search_file(i,"audio.m4s")}" -c copy "{mp4}"'
                )
            if args.danmaku:
                if not search_file(i, "danmaku.xml"):
                    return cmd
                cmd.append(
                    f'{danmaku2ass} "{search_file(i,"danmaku.xml")}" -s {json_data["page_data"]["width"]}x{json_data["page_data"]["height"]} -fn "微软雅黑" -fs 48 -a 0.8 -dm 5 -ds 5 -o "{ass}"'
                )
    return cmd


def run_command(command):
    try:
        subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            encoding="UTF-8",
            errors="ignore",
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"{command}\n{e.stderr}")


all_folder = dir_folder(args.file)
logger.info(f"共发现{len(all_folder)}个视频组")

for i in all_folder:
    try:
        buffer = merge_video(i)
    except:
        logger.error(i)
        continue
    with ThreadPoolExecutor(max_workers=args.thread) as executor:
        executor.map(run_command, buffer)
