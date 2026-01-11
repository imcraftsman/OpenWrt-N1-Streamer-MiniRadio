import json
import urllib.request
import ssl
import os
import subprocess
import sys
import time
# 定义更细致的抓取任务
TASKS = [
    ("Chinese", "language", "chinese"),
    ("Chinese", "language", "mandarin"),
    ("English", "language", "english"),
    # 细化音乐分类
    ("Classical", "tag", "classical"),
    ("Jazz", "tag", "jazz"),
    ("Chillout", "tag", "chillout"),
    ("Ambient", "tag", "ambient"),
    ("Lofi", "tag", "lofi")
]

BASE_URL = "https://de2.api.radio-browser.info/json/stations/by{key}/{value}?lastcheckok=1&limit=250"
OUTPUT_FILE = "/www/radio_data.json"

def fetch_radio():
    print("== 开启全球电台深度搜索 (V3.2 - 细分分类版) ==")
    context = ssl._create_unverified_context()
    all_stations = []
    seen_urls = set()

    for category_label, key, value in TASKS:
        api_url = BASE_URL.format(key=key, value=value)
        print(f"正在抓取 [{category_label}] 组: {value}...")
        
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'N1-Radio-Client/1.0'})
            with urllib.request.urlopen(req, context=context) as response:
                data = json.loads(response.read().decode())
                
                added_count = 0
                for item in data:
                    url = item.get('url_resolved', '')
                    name = item.get('name', '').strip()
                    codec = str(item.get('codec', '')).upper()
                    
                    if url and url not in seen_urls and name:
                        if "MP3" in codec or "AAC" in codec or not codec:
                            station_obj = {
                                "category": category_label, # 现在这里会记录 "Jazz", "Classical" 等
                                "name": name,
                                "url": url,
                                "country": item.get('countrycode', ''),
                                "tags": item.get('tags', '')[:30]
                            }
                            all_stations.append(station_obj)
                            seen_urls.add(url)
                            added_count += 1
                print(f"  --> {category_label} 组新增 {added_count} 个")
        except Exception as e:
            print(f"请求失败: {e}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_stations, f, ensure_ascii=False, indent=2)
            
    print(f"\n== 完成！共计 {len(all_stations)} 个电台。分类包括: {list(set(s['category'] for s in all_stations))} ==")


def update_mpc_robust():
    print("== [1/4] 环境自愈：补齐 MPD 运行目录 ==")
    # 统一路径管理
    DIRS = ["/var/lib/mpd/music", "/var/lib/mpd/playlists", "/var/run/mpd", "/tmp/lib/mpd/playlists"]
    FILES = ["/var/lib/mpd/database", "/var/lib/mpd/state"]
    
    for d in DIRS:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"   已创建目录: {d}")
            
    for f in FILES:
        if not os.path.exists(f):
            open(f, 'a').close() # 类似 touch
            print(f"   已创建文件: {f}")

    print("== [2/4] 进程管理：强制重启 MPD ==")
    # 彻底清理可能残留的僵尸进程并启动
    subprocess.run(["killall", "-9", "mpd"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    #subprocess.run(["/usr/bin/mpd", "/etc/mpd.conf"], stderr=subprocess.DEVNULL)
    # 增加 --stdout 参数通常不是必须，但关键是确保它能立即返回
    #subprocess.run(["/usr/bin/mpd", "/etc/mpd.conf"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    #subprocess.Popen(["/usr/bin/mpd", "/etc/mpd.conf"])
    # 使用 preexec_fn 确保脚本退出后 MPD 继续运行
    #subprocess.Popen(["/usr/bin/mpd", "/etc/mpd.conf"], 
                 # stdout=subprocess.DEVNULL, 
                 # stderr=subprocess.DEVNULL,
                 # preexec_fn=os.setpgrp)
    # 【核心修改】使用 os.system 以后台方式启动，并强制加载配置文件
    # 这样启动的 MPD 会直接挂在系统 init 进程下，不会随 Python 退出而退出
    os.system("/usr/bin/mpd /etc/mpd.conf &")
    
    # 给它一点启动时间
    time.sleep(2)             


    print("== [3/4] 状态探测：等待端口就绪 ==")
    mpc_path = "/usr/bin/mpc"
    ready = False
    for i in range(20): # 最多等待 40 秒
        check = subprocess.run([mpc_path, "version"], capture_output=True, text=True)
        if check.returncode == 0:
            print(f"   ✅ MPD 已就绪 (第 {i+1} 次尝试成功)")
            ready = True
            break
        time.sleep(2)
    
    if not ready:
        print("   ❌ 错误：MPD 启动超时，请检查配置。")
        return

    print("== [4/4] 注入列表：原子化同步 ==")
    JSON_SOURCE = "/www/radio_data.json"
    M3U_FILE = "/tmp/lib/mpd/playlists/global.m3u"
    
    with open(JSON_SOURCE, 'r', encoding='utf-8') as f:
        stations = json.load(f)

    with open(M3U_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for s in stations:
            f.write(f"#EXTINF:-1,{s['name']}\n")
            f.write(f"{s['url']}\n")

    # 执行 MPC 事务
    subprocess.run([mpc_path, "clear"], stdout=subprocess.DEVNULL)
    subprocess.run([mpc_path, "update"], stdout=subprocess.DEVNULL)
    time.sleep(2) # 关键：给 MPD 扫描物理文件的时间
    
    res = subprocess.run([mpc_path, "load", "global"], capture_output=True, text=True)
    
    if res.returncode == 0:
        # 设置初始音量并播放
        subprocess.run([mpc_path, "volume", "85"], stdout=subprocess.DEVNULL)
        subprocess.run([mpc_path, "play", "1"], stdout=subprocess.DEVNULL)
        print(f"   ✅ 同步成功！加载电台: {len(stations)} 个")
        print("== N1 网络收音机已进入工作状态 ==")
    else:
        print(f"   ❌ 加载失败: {res.stderr}")

# import datetime

# LOG_FILE = "/tmp/radio_debug.log"

# def log_debug(msg):
    # """向日志文件写入带时间戳的信息"""
    # now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # with open(LOG_FILE, "a", encoding="utf-8") as f:
        # f.write(f"[{now}] {msg}\n")

# def update_mpc_robust():
    # log_debug("=== 开始执行 update_mpc_robust ===")
    
    # # 1. 检查数据源
    # if not os.path.exists(OUTPUT_FILE):
        # log_debug(f"错误: 找不到数据文件 {OUTPUT_FILE}")
        # return

    # try:
        # # 2. 检查并创建目录
        # if not os.path.exists(PLAYLIST_DIR):
            # os.makedirs(PLAYLIST_DIR)
            # log_debug(f"目录不存在，已创建: {PLAYLIST_DIR}")
        # else:
            # log_debug(f"确认目录已存在: {PLAYLIST_DIR}")

        # # 3. 简单的物理写入测试 (你提议的测试环节)
        # test_file = os.path.join(PLAYLIST_DIR, "boot_test.txt")
        # with open(test_file, "w") as tf:
            # tf.write("Python executed successfully at boot.")
        # log_debug(f"写入测试文件成功: {test_file}")

        # # 4. 生成 M3U
        # m3u_file_path = os.path.join(PLAYLIST_DIR, f"{M3U_NAME}.m3u")
        # with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            # stations = json.load(f)
        
        # with open(m3u_file_path, 'w', encoding='utf-8') as f:
            # f.write("#EXTM3U\n")
            # for s in stations:
                # f.write(f"#EXTINF:-1,{s['name']}\n")
                # f.write(f"{s['url']}\n")
        # log_debug(f"M3U 物理文件已生成: {m3u_file_path}，包含 {len(stations)} 个电台")

        # # 5. 调用 MPC 指令
        # # 注意：在 rc.local 中可能找不到 mpc 命令，我们尝试使用绝对路径
        # mpc_path = "/usr/bin/mpc" # 如果你的 mpc 在别处，请用 which mpc 查一下
        
        # subprocess.run([mpc_path, "clear"], stdout=subprocess.DEVNULL)
        # subprocess.run([mpc_path, "update"], stdout=subprocess.DEVNULL)
        # log_debug("执行 mpc clear 和 update")
        
        # # 给 MPD 扫描时间
        # import time
        # time.sleep(2)
        
        # res = subprocess.run([mpc_path, "load", M3U_NAME], capture_output=True, text=True)
        # if res.returncode == 0:
            # log_debug("mpc load global 成功")
            # # 初始化音量
            # subprocess.run([mpc_path, "volume", "80"], stdout=subprocess.DEVNULL)
        # else:
            # log_debug(f"mpc load 失败，错误输出: {res.stderr}")

    # except Exception as e:
        # log_debug(f"运行中发生异常: {str(e)}")

    # log_debug("=== update_mpc_robust 执行结束 ===")


if __name__ == "__main__":
# 如果输入参数包含 --fetch，则先抓取
    if "--fetch" in sys.argv:
        fetch_radio()
    
    # 无论如何，最后都执行一次本地同步
    update_mpc_robust()
 #----------------------执行指南---------------------
 # 默认运行：  python fetch_set_playlist.py
 #音频源需要更新时运行：python fetch_set_playlist.py --fetch
 
 #-------------白纸级别初始化测试条件----------------------
# # 停止进程
# killall -9 mpd 2>/dev/null

# # 彻底删除整个目录树，而不仅仅是里面的内容
# rm -rf /var/lib/mpd
# rm -rf /tmp/lib/mpd
# rm -rf /var/run/mpd

# # 现在再看，ls 应该会报错 "No such file or directory"
# ls /tmp/lib/mpd/playlists/
# python fetch_set_playlist.py
#-----------------常用检查指令--------------------
# ps | grep mpd
# netstat -tuln | grep 6600

# ls /tmp/lib/mpd/playlists/
# # 返回音源个数
# mpc playlist | wc -l  
# #返回前几个音源
# mpc playlist | head -n 5
