#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import subprocess
import re
import time
from urllib.parse import parse_qs
from collections import OrderedDict

DATA_FILE = "/www/radio_data.json"

def clean_info_for_lcd(raw_result, mpc_id):
    """
    清洗中心：处理 XML、URL 及标准文本格式
    """
    # 预处理：去掉空行，获取所有文本块
    lines = [l.strip() for l in raw_result.split('\n') if l.strip()]
    first_line = lines[0] if lines else ""
    
    artist = "LIVE STREAM"
    title = "Buffering..."
    cover = ""

    # --- 1. 优先解析 XML (如 Smooth FM) ---
    # 只要全文包含 XML 特征，就进入强力提取模式
    if "<?xml" in raw_result:
        # 使用更稳健的正则，忽略大小写并允许换行符
        t_match = re.search(r'<DB_DALET_TITLE_NAME>(.*?)</DB_DALET_TITLE_NAME>', raw_result, re.S)
        a_match = re.search(r'<DB_DALET_ARTIST_NAME>(.*?)</DB_DALET_ARTIST_NAME>', raw_result, re.S)
        img_match = re.search(r'<DB_ALBUM_IMAGE>(.*?)</DB_ALBUM_IMAGE>', raw_result, re.S)
        
        # 提取内容
        extracted_title = t_match.group(1).strip() if t_match else ""
        extracted_artist = a_match.group(1).strip() if a_match else ""
        
        # 只有真正提取到文字才返回，否则向下走保底逻辑
        if extracted_title or extracted_artist:
            return extracted_artist or "Smooth FM", extracted_title or "Music", img_match.group(1) if img_match else ""

    # --- 2. 保底逻辑：反查 JSON 获取电台名 ---
    # 如果第一行是网址，或者第一行包含明显的 XML 标签（解析失败残留），则强制反查
    if first_line.startswith("http") or "<xml" in first_line.lower():
        try:
            if mpc_id:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    stations = json.load(f)
                    idx = int(mpc_id) - 1
                    if 0 <= idx < len(stations):
                        # 这里返回 STATION 和 JSON 里的原始电台名
                        return "STATION", stations[idx]['name'], ""
        except:
            pass
        return "RADIO", "Playing Stream...", ""

    # --- 3. 标准文本分割 (歌手 - 歌名) ---
    if " - " in first_line:
        parts = first_line.split(" - ", 1)
        return parts[0].strip(), parts[1].strip(), ""
    
    # --- 4. 最后的防线 ---
    # 再次检查，防止把 XML 源码直接丢给走马灯
    if "<" in first_line and ">" in first_line:
        return "STREAMING", "Online Radio", ""
    title = html.unescape(title)
    artist = html.unescape(artist)
    return artist, first_line or title, ""

from collections import OrderedDict

from collections import OrderedDict

from collections import OrderedDict

def build_tree(data):
    # 1. 临时存储原始结构的字典（不带计数，方便分类填充）
    raw_tree = {
        "中文电台": {},
        "英文电台": {},
        "音乐分类": {}
    }
    
    zh_keys = ['chinese', 'mandarin', 'cantonese', 'hanyu', '普通话', '广东话']
    
    # 2. 严格分配 ID 并填充数据
    for idx, item in enumerate(data, 1):
        item['mpc_id'] = idx
        cat = str(item.get('category', '')).lower()
        country = str(item.get('country', '')).upper()
        tags = str(item.get('tags', '')).lower()

        if any(k in cat or k in tags for k in zh_keys):
            if country == 'CN': sub = "中国大陆"
            elif country == 'TW': sub = "台湾"
            else: sub = "其它中文"
            raw_tree["中文电台"].setdefault(sub, []).append(item)
        elif 'english' in cat or 'english' in tags:
            raw_tree["英文电台"].setdefault(country, []).append(item)
        else:
            label = item.get('category', '其它风格')
            raw_tree["音乐分类"].setdefault(label, []).append(item)

    # 3. 构建最终带计数的有序字典
    final_tree = OrderedDict()
    
    for main_key, subs in raw_tree.items():
        # 计算大分类下的总数
        total_in_main = sum(len(station_list) for station_list in subs.values())
        if total_in_main == 0: continue # 如果大类下没电台则跳过
            
        main_label = f"{main_key} ({total_in_main})"
        final_tree[main_label] = OrderedDict()
        
        # 排序子分类：常规在前，"其它"在后
        sorted_sub_keys = sorted(subs.keys(), 
                                key=lambda x: (1 if "其它" in x or "Other" in x else 0, x))
        
        for sub_key in sorted_sub_keys:
            station_list = subs[sub_key]
            # 子分类名称带计数
            sub_label = f"{sub_key} ({len(station_list)})"
            final_tree[main_label][sub_label] = station_list
            
    return final_tree

def main():
    sys.stdout.write("Content-Type: application/json; charset=utf-8\n\n")
    try:
        query = os.environ.get('QUERY_STRING', '')
        params = parse_qs(query)
        action = params.get("action", [None])[0]

        if action == "get_list":
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                sys.stdout.write(json.dumps(build_tree(raw_data), ensure_ascii=False))

        elif action == "play":
            mid = params.get("id", [None])[0]
            subprocess.run(["/usr/bin/mpc", "stop"], capture_output=True)
            if mid:
                subprocess.run(["/usr/bin/mpc", "play", str(mid)], capture_output=True)
            else:
                subprocess.run(["/usr/bin/mpc", "play"], capture_output=True)
            
            # ALSA 错误自愈
            time.sleep(0.6)
            check = subprocess.run(["/usr/bin/mpc", "status"], capture_output=True, text=True).stdout
            if "ERROR: Failed to open" in check:
                subprocess.run(["/usr/bin/mpc", "stop"], capture_output=True) # 先停
                subprocess.run(["/usr/bin/mpc", "disable", "1"], capture_output=True) # 假设输出ID是1
                time.sleep(0.3) # 给驱动一点喘息时间
                subprocess.run(["/usr/bin/mpc", "enable", "1"], capture_output=True)
                subprocess.run(["/usr/bin/mpc", "play"], capture_output=True)
            sys.stdout.write(json.dumps({"status": "ok"}))

        elif action == "status":
            # 获取原始状态
            res = subprocess.run(["/usr/bin/mpc", "status"], capture_output=True, text=True).stdout
            
            # 提取 ID
            import re
            id_match = re.search(r'#(\d+)/', res)
            current_id = id_match.group(1) if id_match else None

            # --- 修复右上角信息提取 ---
            # 尝试从原始文本中匹配 kbps 和 Hz (兼容 mpc -v 可能出现的格式)
            bitrate_match = re.search(r'(\d+)\s?kbps', res, re.I)
            sample_match = re.search(r'(\d+\.?\d*)\s?k?Hz', res, re.I)
            
            bitrate = f"{bitrate_match.group(1)}k" if bitrate_match else "LIVE"
            # 如果匹配到 44100 这种大数字，转为 44.1k
            if sample_match:
                s_val = sample_match.group(1)
                sample = f"{float(s_val)/1000}kHz" if float(s_val) > 1000 else f"{s_val}kHz"
            else:
                sample = "STREAM"

            # --- 修复中间显示乱码/URL ---
            from radio_ctl import clean_info_for_lcd # 假设你用了我之前推荐的清洗函数
            artist, title, cover = clean_info_for_lcd(res, current_id)

            status = {
                "playing": "[playing]" in res,
                "buffering": "volume:" in res and "[playing]" not in res and "[paused]" not in res,
                "artist": artist,
                "title": title,
                "id": current_id,
                "bitrate": bitrate,
                "sample": sample
            }
            sys.stdout.write(json.dumps(status))

        elif action == "pause":
            subprocess.run(["/usr/bin/mpc", "pause"])
            sys.stdout.write(json.dumps({"status": "ok"}))

        elif action == "volume":
            val = params.get("value", ["85"])[0]
            subprocess.run(["/usr/bin/mpc", "volume", str(val)])
            sys.stdout.write(json.dumps({"status": "ok"}))

    except Exception as e:
        sys.stdout.write(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
