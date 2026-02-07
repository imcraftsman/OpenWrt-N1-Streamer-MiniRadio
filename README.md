# OpenWrt-N1-Streamer-MiniRadio
Phicomm N1 OpenWrt 网络收音机极简实现方案
本方案基于 Phicomm N1 盒子，在 OpenWrt (Flippy 固件) 环境下，通过最轻量化的 MPD + MPC 组合，实现一个稳定、低延迟的全网音频流播放器。

🚀 核心特性
极简架构：无需安装大型 GUI 插件，占用内存极低（< 5MB）。

高稳定性：解决了 N1 常见的重启后无声、列表丢失、音频设备爆音等问题。

支持广泛：兼容 MP3, AAC, FLAC 等多种全球主流音频流协议。

🛠️ 环境要求
硬件：斐讯 N1 (Phicomm N1)

固件：OpenWrt R25.x.x (Flippy 编译版本)

核心组件：

mpd-full (Music Player Daemon)

mpc (命令行控制客户端)

📂 关键路径说明
项目中主要涉及两个核心配置文件，请确保权限已设置为 0755：

/etc/mpd.conf：MPD 服务端核心配置，定义音频输出驱动及缓存路径。

/etc/autostart_radio.sh：自动化启动脚本，负责环境预热、进程保活、电台注入及防爆音初始化。

📝 实施流程总结
1. 软件安装
在终端执行：

Bash

opkg update
opkg install mpd-full mpc
2. 硬件输出配置
编辑 /etc/mpd.conf，关键点在于将 audio_output 锁定为 N1 的 ALSA 硬件接口：

设备地址：hw:0,0

混音模式：software (确保音量调节不会导致驱动死锁)

3. 自动化逻辑核心
启动脚本 /etc/autostart_radio.sh 实现了以下关键逻辑：

环境初始化：自动创建 /var/lib/mpd/ 下的数据库与播放列表目录。

网络同步等待：在脚本开头加入 sleep 机制，确保系统 DNS 解析和 PPPoE 拨号完全就绪。

慢速注入技术：在循环添加 URL 时加入 sleep 2，为 MPD 解析不同协议（如 HTTPS/FLAC）提供充足的握手时间。

防爆音重置：通过 Stop -> Sleep -> Play 序列，解决 N1 HDMI/AV 输出在初始化时的异常电流声。

4. 换台指令参考
模型运行后，可通过标准 mpc 指令快速换台：

Bash

mpc stop; sleep 1; mpc play [电台编号]
⚠️ 避坑指南 (经验总结)
协议选择：在 N1 环境下，MP3 直流 的稳定性远高于 HLS (.m3u8)。若遇到 Empty reply from server，通常是服务器拦截或切片下载超时。

权限管理：确保 /var/lib/mpd/ 目录对 root 或 mpd 用户有写权限，否则数据库无法保存。

后台解耦：所有自定义脚本必须以 & 结尾放入后台运行，严禁阻塞 OpenWrt 系统的主启动链。

仓库文件说明：

mpd.conf - 查看详细配置

autostart_radio.sh - 查看脚本源码


## 📻 流媒体传输协议对比 (N1 适配参考)

在网络收音机领域，选择正确的流媒体协议直接决定了 N1 运行的**稳定性**与**听感**。以下是针对 N1 (OpenWrt) 环境的实测对比：

| 协议类型 | 全称 | N1 实测表现 | 技术特点 | 推荐指数 |
| :--- | :--- | :--- | :--- | :--- |
| **MP3** | MPEG-1 Audio Layer III | **最稳** | 兼容性无敌，码率固定，对 CPU 和网络抖动不敏感。 | ⭐⭐⭐⭐⭐ |
| **AAC** | Advanced Audio Coding | **优良** | 相同码率下音质优于 MP3，是目前全球主流电台的核心格式。 | ⭐⭐⭐⭐ |
| **FLAC** | Free Lossless Audio Codec | **吃带宽** | **无损音质**。数据量巨大，若网络波动易造成解码停顿，适合发烧友。 | ⭐⭐⭐ |
| **HLS** | HTTP Live Streaming (`.m3u8`) | **易断流** | 将音频切成无数小片传输。在 N1 环境下，若握手稍慢，极易报 Empty reply。 | ⭐⭐ |

### 💡 为什么首选 MP3/AAC？
* **数据连续性**：MP3/AAC 通常是连续流 (Continuous Stream)，N1 只需建立一次连接即可持续接收音频。
* **容错性**：面对网络微小抖动，MP3 协议具有更好的容错机制，不会像 HLS 那样因为某个分片 (Segment) 下载失败而导致整个播放列表跳台。
* **资源占用**：MP3 解码对 N1 的 CPU 几乎零负载，能够保证后台长时间运行不发热。


下一步计划
[ ] 扩充全球高清音频流源 (STATIONS 数组优化)

[ ] 开发基于 Web 的控制 UI 页面

## N1-Radio: 自动化网络收音机项目阶段总结
本项目致力于在基于 LEDE/OpenWrt 系统的斐讯 N1 盒子上，构建一个全自动、高可靠性的网络广播播放系统。以下是现阶段已实现的核心功能与技术突破：

### 🚀 核心成就概览
1. 动态音频源自动化抓取
API 集成：成功对接 de2.api.radio-browser.info 开源电台数据库。

精准过滤：实现了基于 tags（如 news, jazz）及电台名称关键词的自动化筛选机制，确保音频流质量。

本地化持久化：抓取到的 1000+ 电台元数据自动保存为本地 radio_data.json，减少了对 API 的频繁请求。

2. 播放列表（M3U）智能管理
原子化同步：Python 脚本自动将 JSON 数据转换为标准的 global.m3u 播放列表格式。

动态更新机制：实现了每次启动时自动清理旧列表并重新注入新列表的功能，确保电台链接的时效性。

绝对路径补齐：解决了 MPD 对播放列表存放路径的严格要求，通过 Python 自动维护 /tmp/lib/mpd/playlists/ 目录结构。

3. 系统级 MPD 进程自主受控
启动权回收：通过 disable 系统默认的 mpd 初始化脚本，彻底解决了系统原生启动项无法加载外部 URL 的问题。

自愈式启动逻辑：

环境修复：脚本运行前自动检测并创建缺失的数据库文件、状态文件及 PID 目录，消除 No such file 报错。

独立进程托管：放弃了不稳定的 subprocess 管道模式，改用 os.system("/usr/bin/mpd /etc/mpd.conf &") 实现 MPD 进程的彻底脱离与常驻。

端口探测技术：引入了基于 mpc version 的轮询探测机制，确保在 MPD 端口完全监听后再进行列表注入，提高了启动成功率。

4. 深度配置优化（Conf Tuning）
抗抖动处理：将音频缓冲区（audio_buffer_size）从默认值提升至 8192KB，显著缓解了跨境电台流的卡顿问题。

超时断舍离：配置 connection_timeout "10"，防止 MPD 进程因尝试连接无效 URL 而陷入无限期僵死（Timeout）状态。

日志重定向：将日志文件由内存或磁盘持久区重定向至 /tmp/mpd.log，既保护了 N1 的 Flash 寿命，又实现了实时故障排查。

### 🛠 技术栈
宿主系统：LEDE / OpenWrt (Phicomm N1)

后端语言：Python 3

服务组件：Music Player Daemon (MPD) / MPC

数据格式：JSON / M3U / ALSA (Audio)

### 本阶段成果： 
 1）修改 /etc/mpd.conf
 
 2）新增 fetch_set_playlist.py
 
 3）执行：/etc/init.d/mpd disable 停止系统对mpd启动。 本地启动项增加  
 
 #收音机
 
(sleep 10 && python /root/fetch_set_playlist.py) &

📈 下一阶段目标
[ ] Web 控制端：开发 radio.html，实现手机端远程选台。

[ ] 精简化播放：实现电台分类筛选功能。

[ ] 稳定性监控：增加脚本自动检测 MPD 状态并自动重启的守护逻辑。

# 2026.1.13
# 📻 N1 Radio V2.6 Pro 全量技术架构白皮书

本项目是专为 N1 (Armbian/OpenWrt/LEDE) 打造的高级网络广播控制系统。它不仅是一个前端界面，更是一套集成了**元数据深度清洗**、**硬件自愈**与**闭环交互逻辑**的嵌入式音频解决方案。

---

## 📂 项目文件列表

| 文件路径 | 职能描述 | 关键技术 |
| :--- | :--- | :--- |
| `/www/radio.html` | **交互总控** | 响应式布局、闭环导航算法、Safari 兼容性补丁。 |
| `/www/cgi-bin/radio_ctl.py` | **后端引擎** | XML 过滤、ALSA 自愈逻辑、JSON 动态计数。 |
| `/www/cgi-bin/radio_data.json` | **结构化数据库** | 三级树状分类、电台流地址与图标配置。 |
| `/etc/mpd.conf` | **系统级配置** | 定义 ALSA 设备参数、代理服务器、缓存策略。 |
| `/usr/bin/mpc` | **物理执行器** | 通过命令行操控底层 MPD 服务。 |

---

## 🛠️ 核心技术架构汇总

### 1. 后端数据处理与自愈层
* **智能元数据清洗 (Smart Metadata Engine)**：针对部分电台（如 Smooth FM）返回的非标准 XML，通过 `clean_info_for_lcd` 函数进行深度解析，支持 `re.S` 模式跨行正则匹配，彻底过滤 XML 标签及 URL 干扰。
* **Single Mode 保护机制**：强制设置 `mpc single on`，解决 SSL 握手失败或流中断时播放器疯狂自动切台的顽疾。
* **ALSA 驱动自愈**：针对 `hw:0,0` 报错，内置了“停止-禁用-延迟-启用-播放”的硬件复位序列，有效解决音频设备被抢占或采样率切换导致的驱动卡死。

### 2. 前端闭环控制算法
* **上下文锁定导航**：点击电台时自动赋予 `currentGroup` 作用域，使键盘上下键与 PREV/NEXT 按钮仅在当前最小子分类内循环，实现物理级的操作隔离。
* **双向状态对齐**：支持“后台驱动前端”。页面加载时，系统根据当前播放电台 ID 自动反向执行菜单展开、位置高亮及导航上下文初始化。
* **智能音量交互**：引入 `isDraggingVol` 标记，解决了轮询数据回传导致的滑块“位置回弹”手感问题。

### 3. 极致响应式与布局兼容
* **多维适配**：采用 `max-height: 500px` 媒体查询，在手机横屏下自动应用 `scale` 缩放，确保 LCD 屏、控制按钮与音量条全可见。
* **Safari 强制策略**：引入 `force-hide` CSS 类，通过 JavaScript 解决 iOS Safari 在横屏模式下无法自动收起侧边栏的兼容性 Bug。
* **仿真 LCD 显示**：纯 CSS 实现的双文本无缝走马灯，配合动态 Visualizer（波形图），提供沉浸式收听体验。

---

## 🚀 未来可扩展项 (Roadmap)

为了进一步提升系统的专业性，后续版本将围绕以下方向进行迭代：

### 电台管理系统 (V3.0)
* **收藏夹功能**：修改 `radio_data.json` 保存逻辑，允许用户在界面上实时标记 Favorite，并生成独立的“收藏夹”虚拟分类。
* **在线更新**：支持通过 Web 界面直接添加新电台流地址。

### 增强型功能模块
* **电台录制**：通过后端调用 `ffmpeg` 或 `mpc-record` 捕获当前流媒体，保存为本地 `.mp3` 文件。
* **定时关机 (Sleep Timer)**：前端增加倒计时插件，到时自动执行 `mpc stop`。

### 系统固化与备份
* **备份机制**：提供一键备份脚本，将 `/www/cgi-bin` 及配置文件打包，防止 LEDE/OpenWrt 系统固件升级导致的数据丢失。
* **系统服务化**：将 `radio_ctl.py` 逻辑封装为后台守护进程，提升响应速度。

---

## 📊 系统健康评估

| 模块 | 状态 | 评价 |
| :--- | :--- | :--- |
| **操控稳定性** | 🟢 极高 | 闭环算法消除了误操作空间。 |
| **设备兼容性** | 🟢 优秀 | 适配 PC、安卓、iOS（横/竖屏）。 |
| **容错自愈力** | 🟢 强 | 已解决 SSL 报错乱跳台及驱动卡死问题。 |
| **UI 美观度** | 🟢 专业 | 专业 LCD 仿真效果与动态波形反馈流畅。 |

---

**© 2024 N1 Radio Project | 持续进化中...**

#系统配置 文件：/etc/rc.local增加一下内容：

# 恢复从 /etc/alsa/asound.state 读取的声卡音量与开关状态，防止开机静音
# 核心功能：强制加载自定义生成的声卡配置文件
# 适用场景：解决 N1 重启后 HDMI 音频自动变为静音(MM)的问题
alsactl -f /etc/alsa/asound.state restore >/dev/null 2>&1

#收音机
(sleep 10 && python /root/fetch_set_playlist.py) &
