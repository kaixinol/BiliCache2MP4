from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import multiprocessing
from pathlib import Path
import re
import argparse
from loguru import logger
import subprocess
import shutil
import xml.etree.ElementTree as ET
from curl_cffi import requests
import sys
import threading

# 初始化日志
logger.remove()
logger.add(sys.stderr, level="DEBUG", diagnose=True, backtrace=True)

# 参数解析
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
args.file = Path(args.file).resolve()
args.output = Path(args.output).resolve()

# 确定 danmaku2ass 命令列表
danmaku2ass_cmd = (
    ["danmaku2ass.exe"]
    if Path("danmaku2ass.exe").exists()
    else ["python", "danmaku2ass.py"]
)

# 确定 ffmpeg 路径和命令列表
ffmpeg_path = args.ffmpeg or shutil.which("ffmpeg")
if not ffmpeg_path:
    parser.error("无法在环境变量中找到 ffmpeg，请使用 -f 参数指定路径")
try:
    subprocess.run(
        [ffmpeg_path, "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    ffmpeg_cmd = [ffmpeg_path, "-hide_banner", "-loglevel", "error", "-n"]
except (subprocess.SubprocessError, FileNotFoundError):
    parser.error(f"ffmpeg 在路径 '{ffmpeg_path}' 不可用")


def illegal_filter(name: str, maxlen: int = 48) -> str:
    t = re.sub(r'[<>:"/\\|?*]', " ", name)
    t = t.rstrip(" .")
    return t[:maxlen]


def dir_folder(path: Path):
    if not path.exists():
        logger.error(f"路径不存在: {path}")
        return []
    return [p for p in path.iterdir() if p.is_dir()]


def search_file(dir_path: Path, pattern: str):
    matches = [p for p in dir_path.rglob("*") if pattern in p.name]
    if not matches:
        return None
    return matches[0] if len(matches) == 1 else matches


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"读取JSON失败 {path}: {e}")
        return None


def write_nfo(data: dict, path: Path, mode: str = "folder"):
    def download_cover():
        url = data["cover"]
        out = path.parent / (
            f"{illegal_filter(data['title'])}-cover.png"
            if mode != "folder"
            else "cover.png"
        )
        if out.exists():
            return
        resp = requests.get(url)
        if resp.status_code == 200:
            out.write_bytes(resp.content)
        else:
            logger.error(f"下载封面失败: {url} 状态 {resp.status_code}")

    movie = ET.Element("movie")
    ET.SubElement(movie, "title").text = data["title"]
    credits = ET.SubElement(movie, "credits")
    credits.text = (
        f"{data.get('owner_name', 'UNKNOWN')}[{data.get('owner_id', '')}]"
        if data.get("owner_id")
        else "UNKNOWN"
    )
    ET.SubElement(movie, "year").text = str(
        datetime.fromtimestamp(data["time_update_stamp"] / 1000).year
    )
    ET.SubElement(movie, "uniqueid", {"type": "bilibili"}).text = f"av{data['avid']}"
    ET.SubElement(movie, "aired").text = datetime.fromtimestamp(
        data["time_update_stamp"] / 1000
    ).strftime("%Y-%m-%d")
    download_cover()
    ET.ElementTree(movie).write(path, encoding="utf-8", xml_declaration=True)


def build_ffmpeg_cmd(inputs: list[str], output: Path):
    return ffmpeg_cmd + inputs + ["-c", "copy", str(output)]


def build_danmaku_cmd(danmaku_path: Path, size: str, output: Path):
    return danmaku2ass_cmd + [
        str(danmaku_path),
        "-s",
        size,
        "-fn",
        "微软雅黑",
        "-fs",
        "48",
        "-a",
        "0.8",
        "-dm",
        "5",
        "-ds",
        "5",
        "-o",
        str(output),
    ]


def generate_merge_video(group_dir: Path) -> list[list[str]]:
    cmds = []
    folders = dir_folder(group_dir)
    logger.info(f"处理 {group_dir}: {len(folders)} 子文件夹")
    for idx, item in enumerate(folders, start=1):
        entry = search_file(item, "entry.json")
        if not entry:
            logger.warning(f"{item} 缺少 entry.json")
            continue
        data = read_json(Path(entry))
        if not data:
            continue
        title = illegal_filter(data["title"])
        part = illegal_filter(data["page_data"].get("part", data["title"]))
        vid_file = search_file(item, "video.m4s")
        if not vid_file:
            flvs = list(item.rglob("lua.*"))
            vid_file = list(flvs[0].rglob("*.blv")) if flvs else None
        if not vid_file:
            logger.warning(f"{item} 没有视频文件")
            continue

        if args.folder:
            out_dir = args.output / title
            out_dir.mkdir(parents=True, exist_ok=True)
            mp4 = out_dir / f"{part}.mp4"
            ass = out_dir / f"{part}.ass"
        else:
            name = f"{title}-{part}.mp4" if idx > 1 else f"{title}.mp4"
            mp4 = args.output / name
            ass = args.output / name.replace(".mp4", ".ass")

        inputs = []
        if isinstance(vid_file, list):
            for f in vid_file:
                inputs += ["-i", str(f)]
        else:
            inputs += ["-i", str(vid_file)]
            audio = search_file(item, "audio.m4s")
            if audio:
                inputs += ["-i", str(audio)]
        cmds.append(build_ffmpeg_cmd(inputs, mp4))

        if args.danmaku:
            danmaku = search_file(item, "danmaku.xml")
            if danmaku:
                size = f"{data['page_data']['width']}x{data['page_data']['height']}"
                cmds.append(build_danmaku_cmd(Path(danmaku), size, ass))

        if args.nfo:
            write_nfo(
                data, mp4.with_suffix(".nfo"), "folder" if args.folder else "file"
            )
    return cmds


def run_command(cmd: list[str]):
    thread_name = threading.current_thread().name
    logger.debug(f"[{thread_name}] 开始执行命令: {' '.join(cmd)}")
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        disp = " ".join([("ffmpeg" if c == ffmpeg_path else c) for c in cmd])
        logger.debug(f"[{thread_name}] 命令执行完成: {disp}")
    except subprocess.CalledProcessError as e:
        logger.error(f"[{thread_name}] 执行失败: {e.stderr}")


logger.info(f"开始处理: {args.file}")
if not args.file.exists():
    logger.error(f"路径不存在: {args.file}")
    sys.exit(1)
tasks = []
for grp in dir_folder(args.file):
    tasks.extend(generate_merge_video(grp))
with ThreadPoolExecutor(max_workers=args.thread) as ex:
    ex.map(run_command, tasks)
