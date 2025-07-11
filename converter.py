from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing
from pathlib import Path
import re
import argparse
from loguru import logger
import subprocess
import shutil
from curl_cffi import requests
from datetime import datetime
from lxml import etree
parser = argparse.ArgumentParser()
parser.add_argument(
    "-f", "--ffmpeg", type=str, help="FFmpeg的路径，默认从环境变量中寻找"
)
parser.add_argument(
    "-folder", action="store_true", default=False, help="是否每一个视频一个文件夹"
)
parser.add_argument(
    "-danmaku", action="store_true", default=False, help="是否转换.xml到弹幕文件.ass"
)
parser.add_argument("file", metavar="FILE", help="b站缓存文件文件夹")
parser.add_argument(
    "-o",
    "--output",
    type=str,
    default=Path.cwd(),
    help="释放的位置，默认为本脚本所在目录",
)
parser.add_argument(
    "-t",
    "--thread",
    type=int,
    default=multiprocessing.cpu_count(),
    help="多线程数，默认为cpu当前核数",
)
parser.add_argument("-nfo", action="store_true", default=False, help="是否添加nfo文件")
args = parser.parse_args()

# 初始化
danmaku2ass = (
    "danmaku2ass.exe" if Path("danmaku2ass.exe").exists() else "python danmaku2ass.py"
)
args.file = Path(args.file).resolve()  # 使用绝对路径
args.output = Path(args.output).resolve()  # 使用绝对路径

# 确定 ffmpeg 路径
if args.ffmpeg:
    ffmpeg_path = args.ffmpeg
else:
    # 从环境变量中寻找 ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        parser.error("无法在环境变量中找到 ffmpeg，请使用 -f 参数指定路径")

# 验证 ffmpeg 是否可用
try:
    subprocess.run(
        [ffmpeg_path, "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    # 添加 ffmpeg 参数
    ffmpeg_cmd = f'"{ffmpeg_path}" -hide_banner -loglevel error -n'
except (subprocess.SubprocessError, FileNotFoundError):
    parser.error(f"ffmpeg 在路径 '{ffmpeg_path}' 不可用")

def write_nfo(data: dict, path: Path, mode="folder"):
    def download():
        url = data["cover"]
        response = requests.get(url)
        if response.status_code == 200:
            with open(
                (path.parent / f"{illegal_filter(data['title'])}-poster.png")
                if mode != "folder"
                else (path.parent / "poster.png"),
                "wb",
            ) as f:
                f.write(response.content)
        else:
            logger.error(f"下载封面失败: {url}，状态码: {response.status_code}")

    movie = etree.Element("movie")

    etree.SubElement(movie, "title").text = data["title"]
    etree.SubElement(movie, "credits").text = (
        f"{data['owner_name']}[{data['owner_id']}]"
        if data.get("owner_id", "")
        else "UNKNOWN"
    )

    etree.SubElement(movie, "year").text = str(
        datetime.fromtimestamp(data["time_update_stamp"] / 1000).year
    )

    # 正确使用 CDATA 包裹 plot 内容
    plot_text = (
        f'原始视频：<a href="https://www.bilibili.com/video/{f"av{data['avid']}"}/">'
        f"av{data['avid']}</a><br/><br/>{data['title']}"
    )
    plot_elem = etree.SubElement(movie, "plot")
    plot_elem.text = etree.CDATA(plot_text)

    etree.SubElement(movie, "uniqueid", type="bilibili").text = f"av{data['avid']}"
    etree.SubElement(movie, "aired").text = datetime.fromtimestamp(
        data["time_update_stamp"] / 1000
    ).strftime("%Y-%m-%d")
    try:
        download()
    except:
        logger.error(f"下载封面失败: {data['cover']}")
    tree = etree.ElementTree(movie)
    tree.write(str(path), encoding="utf-8", xml_declaration=True, pretty_print=True)


# 仅查找目录，返回列表
def dir_folder(n: str):
    try:
        path = Path(n).resolve()  # 转为绝对路径
        if not path.exists():
            logger.error(f"路径不存在: {path}")
            return []
        return [path / i for i in path.iterdir()]
    except OSError as e:
        logger.error(f"读取目录 {n} 时出错: {e}")
        return []


# 标题中的非法字符过滤
def illegal_filter(t: str):
    return re.sub(r'[\/:"*?<>|]', " ", t).rstrip().strip(".")


# 搜索文件
def search_file(name: str, s: str):
    try:
        file_list = []
        for path in Path(name).rglob("*"):
            if s in path.name:
                file_list.append(path)
        return file_list[0] if len(file_list) == 1 else file_list
    except OSError as e:
        logger.error(f"搜索文件 {s} 时出错: {e}")
        return None


def read_json(n: str):
    try:
        with open(Path(n), "r", encoding="utf-8") as load_f:
            load_dict = json.load(load_f)
        return load_dict
    except OSError as e:
        logger.error(f"读取JSON文件 {n} 时出错: {e}")
        return None


# 有的json没有part，只有title
def read_title(load_dict: dict):
    try:
        if not load_dict:
            return "未知标题"
        if "part" not in load_dict["page_data"]:
            return illegal_filter(load_dict["title"])
        else:
            return illegal_filter(load_dict["page_data"]["part"])
    except OSError as e:
        logger.error(f"读取标题时出错: {e}")
        return "未知标题"


# 生成指令list
def generate_merge_video(fn: str):
    cmd = []
    folders = dir_folder(fn)
    logger.info(f"处理目录: {fn}, 找到 {len(folders)} 个子文件夹")
    l = 0
    for i in folders:
        l += 1
        entry_json = search_file(i, "entry.json")
        if not entry_json:
            logger.warning(f"在 {i} 中找不到 entry.json 文件")
            continue

        json_data = read_json(entry_json)
        if not json_data:
            logger.warning(f"无法读取 {entry_json} 文件")
            continue

        filtered_title = illegal_filter(json_data["title"])
        filtered_part_title = read_title(json_data)

        video_file = search_file(i, "video.m4s") or list(
            (i / "lua.flv.bili2api.80").rglob("*.blv")
        )
        if not video_file:
            logger.warning(f"在 {i} 中找不到视频文件")
            continue

        if args.folder:
            folder = args.output / filtered_title

            if len(folders) != 1:
                mp4 = folder / (filtered_title + filtered_part_title + f"-P{l}.mp4")
                ass = folder / (filtered_title + filtered_part_title + f"-P{l}.ass")
            else:
                mp4 = folder / (filtered_title + filtered_part_title + ".mp4")
                ass = folder / (filtered_title + filtered_part_title + ".ass")
            if not folder.exists():
                folder.mkdir(parents=True)

            audio_file = search_file(i, "audio.m4s")
            if not isinstance(video_file, list):
                if not audio_file:
                    cmd.append(f'{ffmpeg_cmd} -i "{video_file}" -c copy "{mp4}"')
                else:
                    cmd.append(
                        f'{ffmpeg_cmd} -i "{video_file}" -i "{audio_file}" -c copy "{mp4}"'
                    )
            else:  # blv
                input_files = " ".join(f'-i "{i}"' for i in video_file)
                cmd.append(f"{ffmpeg_cmd} {input_files} -c copy {mp4}")

            if args.danmaku:
                danmaku_file = search_file(i, "danmaku.xml")
                if not danmaku_file:
                    logger.info(f"在 {i} 中找不到弹幕文件")
                    continue
                cmd.append(
                    f'{danmaku2ass} "{danmaku_file}" -s {json_data["page_data"]["width"]}x{json_data["page_data"]["height"]} -fn "微软雅黑" -fs 48 -a 0.8 -dm 5 -ds 5 -o "{ass}"'
                )
            if args.nfo:
                write_nfo(json_data, folder / (mp4.stem + ".nfo"))
        else:
            if len(folders) != 1:
                mp4 = args.output / (
                    filtered_title + filtered_part_title + f"-P{l}.mp4"
                )
                ass = args.output / (
                    filtered_title + filtered_part_title + f"-P{l}.ass"
                )
            else:
                mp4 = args.output / (filtered_title + filtered_part_title + ".mp4")
                ass = args.output / (filtered_title + filtered_part_title + ".ass")
            if not isinstance(video_file, list):
                audio_file = search_file(i, "audio.m4s")
                if not audio_file:
                    cmd.append(f'{ffmpeg_cmd} -i "{video_file}" -c copy "{mp4}"')
                else:
                    cmd.append(
                        f'{ffmpeg_cmd} -i "{video_file}" -i "{audio_file}" -c copy "{mp4}"'
                    )
            else:
                input_files = " ".join(f'-i "{i}"' for i in video_file)
                cmd.append(f"{ffmpeg_cmd} {input_files} -c copy {mp4}")
            if args.danmaku:
                danmaku_file = search_file(i, "danmaku.xml")
                if not danmaku_file:
                    logger.info(f"在 {i} 中找不到弹幕文件")
                    continue
                cmd.append(
                    f'{danmaku2ass} "{danmaku_file}" -s {json_data["page_data"]["width"]}x{json_data["page_data"]["height"]} -fn "微软雅黑" -fs 48 -a 0.8 -dm 5 -ds 5 -o "{ass}"'
                )
            if args.nfo:
                write_nfo(json_data, args.output / (mp4.stem + ".nfo"), "file")
    return cmd


def run_command(command: str):
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
        print(command.replace(ffmpeg_cmd, "ffmpeg"))
    except subprocess.CalledProcessError as e:
        logger.error(f"{command}\n{e.stderr}")


logger.info(f"开始处理视频文件: {args.file}")
if not args.file.exists():
    logger.error(f"路径不存在: {args.file}")
    exit(1)

all_folder = dir_folder(args.file)
logger.info(f"共发现{len(all_folder)}个视频组")

if not Path(args.output).exists():
    Path(args.output).mkdir(parents=True)

for i in all_folder:
    buffer = generate_merge_video(i)
    if buffer and len(buffer) > 0:  # 确保 buffer 不是 None 或空列表
        with ThreadPoolExecutor(max_workers=args.thread) as executor:
            executor.map(run_command, buffer)
    else:
        logger.warning(f"目录 {i} 没有生成任何命令")
