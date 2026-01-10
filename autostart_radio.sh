#!/bin/sh

# 定义电台列表（全部使用 http 确保兼容性）
STATIONS="
http://stream.zeno.fm/0r0xa792kwzuv
http://lhttp.qingting.fm/live/270/64k.mp3
http://icecast.ndr.de/ndr/ndr2/niedersachsen/mp3/128/stream.mp3
http://ice.somafm.com/groovesalad
https://rfichinois96k.ice.infomaniak.ch/rfichinois-96k.mp3
http://stream.radioparadise.com/flacm
"

{
    # 1. 环境准备
    mkdir -p /var/lib/mpd/music /var/lib/mpd/playlists /var/run/mpd
    touch /var/lib/mpd/database /var/lib/mpd/state
    amixer -c 0 set PCM unmute 100% >/dev/null 2>&1

    # 2. 干净启动 MPD
    /usr/bin/killall -9 mpd 2>/dev/null
    sleep 1
    /usr/bin/mpd /etc/mpd.conf >/dev/null 2>&1
    
    # 3. 循环等待 MPD 就绪
    I=0; while [ ! -S /var/run/mpd/socket ] && [ $I -lt 15 ]; do sleep 1; I=$((I+1)); done

    # 4. 注入列表并实时反馈（这是你要的检查功能）
    /usr/bin/mpc clear >/dev/null
    for url in $STATIONS; do
         /usr/bin/mpc add "$url" >/dev/null
         #添加链接列表后要等待，否则会造成假添加
        sleep 2
    done
    
    # 5. 播放第一台
    /usr/bin/mpc volume 85 >/dev/null
    /usr/bin/mpc play 1
    
    # 6. N1 防爆音重置
    sleep 1; /usr/bin/mpc stop; sleep 1; /usr/bin/mpc play 1

} >/tmp/radio_boot.log 2>&1 &


echo "----------============== N1网络收音机 ==============--------------"
echo "电台列表："
mpc playlist
echo ""
echo "--------即将播放，如声音暂时没有出现，一定要请耐心等待-----------"
echo "换台指令举例：  mpc stop; sleep 1; mpc play n"

exit 0
