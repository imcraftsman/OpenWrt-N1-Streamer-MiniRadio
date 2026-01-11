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
