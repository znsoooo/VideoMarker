import os
import csv
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class VideoPlayer:
    def __init__(self, path):
        self.path = path

        # 初始化视频捕获对象
        self.cap = cv2.VideoCapture(path)

        # 检查视频是否成功打开
        if not self.cap.isOpened():
            print(f'无法打开视频文件: {path}')
            exit()

        # 获取视频属性
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame = self.cap.read()[1]

        # 初始化变量
        self.idx = 0
        self.paused = False
        self.clock = time.time()

    def MoveFrame(self, count=1):
        """向后移动指定帧数"""
        new_idx = max(0, min(self.frame_count - 1, self.idx + int(count)))
        if new_idx == self.idx:
            pass
        elif new_idx == self.idx + 1:
            self.frame = self.cap.read()[1]
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_idx)
            self.frame = self.cap.read()[1]
        self.idx = new_idx
        return self.frame is not None

    def GetNextFrame(self):
        """处理按键事件"""
        self.clock += 1 / self.fps
        delay = self.clock - time.time()
        key = cv2.waitKeyEx(max(int(1000 * delay), 1))

        keymap = {
            0x250000:  -5 * self.fps,  # LEFT
            0x270000:  +5 * self.fps,  # RIGHT
            0x210000: -60 * self.fps,  # PAGE_UP
            0x220000: +60 * self.fps,  # PAGE_DOWN
            0x240000: -self.frame_count,  # HOME
            0x230000: +self.frame_count,  # END
        }

        if key == -1:
            pass
        elif key == 27 or key == ord('q'):  # ESC/Q键退出
            return False
        elif key == ord(' '):  # 空格键: 暂停/继续
            self.paused = not self.paused
        elif self.paused and key == 0x250000:  # 左箭头
            return self.MoveFrame(-1)
        elif self.paused and key == 0x270000:  # 右箭头
            return self.MoveFrame(+1)
        elif key in keymap:
            return self.MoveFrame(keymap[key])
        else:
            self.OnKeyPress(key)

        return self.MoveFrame(not self.paused)

    def Run(self):
        """视频播放主循环"""
        while self.GetNextFrame():
            self.ShowFrame()

        # 释放资源
        self.cap.release()
        cv2.destroyAllWindows()

    def ShowFrame(self):
        cv2.imshow('Video Player', self.frame)

    def OnKeyPress(self, key):
        pass


class Recorder:
    def __init__(self, path):
        self.path = path
        self.stat = self.Load()

    def Index(self, idx):
        if not self.stat or idx < self.stat[0][0]:
            return -1
        for idx_stat, (idx2, group_id2) in enumerate(reversed(self.stat)):
            if idx2 <= idx:
                return len(self.stat) - idx_stat - 1

    def Insert(self, idx, group_id):
        idx_stat = self.Index(idx)
        item = (idx, group_id)
        if idx_stat == -1:
            self.stat.insert(0, item)
        elif idx == self.stat[idx_stat][0]:
            self.stat[idx_stat] = item
        else:
            self.stat.insert(idx_stat + 1, item)
        self.Update()

    def Remove(self, idx):
        idx_stat = self.Index(idx)
        if idx_stat >= 0:
            self.stat.pop(idx_stat)
        self.Update()

    def Stat(self, idx):
        # 计算时长统计
        group_id = 0
        count = [0] * 5  # [总共, 手动, 自动, 停车, 结束]
        idx_stat = self.Index(idx)
        if idx_stat >= 0:
            for (idx2, group_id2), (idx3, group_id3) in zip(self.stat[:idx_stat], self.stat[1:]):
                count[0] += idx3 - idx2
                count[group_id2] += idx3 - idx2
            idx2, group_id = self.stat[idx_stat]
            count[0] += idx - idx2
            count[group_id] += idx - idx2
        return group_id, count

    def Update(self):
        """保存到CSV文件"""
        stat2 = []
        for idx, group_id in self.stat:
            if not stat2 or stat2[-1][1] != group_id:
                stat2.append((idx, group_id))
        self.stat = stat2
        with open(self.path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['idx', 'group'])
            writer.writerows(self.stat)

    def Load(self):
        """从CSV文件中载入"""
        try:
            with open(self.path, 'r', newline='') as f:
                return [(int(idx), int(group_id)) for idx, group_id in list(csv.reader(f))[1:]]
        except Exception:
            return []


class VideoMarker(VideoPlayer):
    def __init__(self, path):
        VideoPlayer.__init__(self, path)

        # 计时统计
        self.recorder = Recorder(os.path.splitext(path)[0] + '.csv')

        # 文本显示位置
        self.mask_size = (280, 140)
        self.text_pos = (10, 30)
        self.stats_pos = (10, 60)

        font_path = 'C:/Windows/Fonts/msyh.ttc'
        self.font1 = ImageFont.truetype(font_path, 28)
        self.font2 = ImageFont.truetype(font_path, 20)

    def ShowFrame(self):
        self.DisplayStats()
        cv2.imshow('Video Marker', self.frame)

    def OnKeyPress(self, key):
        if key == 0x2e0000:  # DEL键
            self.recorder.Remove(self.idx)
        elif ord('1') <= key <= ord('4'):
            # 记录当前时间点
            group_id = key - ord('0')
            self.recorder.Insert(self.idx, group_id)
        else:
            print(f'OnKeyPress: {key} ({hex(key)})')

    def FormatTime(self, frames):
        """将帧数转换为时间字符串 (MM:SS.NNN)"""
        seconds = frames / self.fps
        seconds_int = int(seconds)
        minutes, secs = divmod(seconds_int, 60)
        ms = int((seconds - seconds_int) * 10)
        return f'{minutes:02d}:{secs:02d}.{ms:01d}'

    def FormatPercent(self, frames, total):
        return f'{self.FormatTime(frames)} ({frames / (total or 1):.1%})'

    def FormatStat(self):
        """更新计时统计"""
        group_id, count = self.recorder.Stat(self.idx)
        if not count[0]:
            return ''

        # 计算时长统计百分比
        labels = ['接管', '脱手', '停车', '结束']
        total = count[0] - count[4]
        stat_text = (
            f'{self.FormatTime(total)} ({labels[group_id - 1]})\n'
            f'{labels[1]}时间：{self.FormatPercent(count[2] + count[3], total)}\n'
            f'{labels[0]}时间：{self.FormatPercent(count[1], total)}\n'
            f'{labels[2]}时间：{self.FormatPercent(count[3], total)}\n'
        )

        return stat_text

    def DisplayStats(self):
        """在屏幕上显示时间信息"""
        w, h = self.text_pos
        texts = self.FormatStat().splitlines()
        if not texts:
            return

        text_img = Image.new('RGB', self.mask_size, (0, 0, 0))
        draw = ImageDraw.Draw(text_img)
        for i, text in enumerate(texts):
            font = self.font1 if i == 0 else self.font2
            draw.text((w, h + 30 * i - font.size), text, font=font, fill=(0, 255, 0))
        x, y = self.mask_size
        self.frame[:y, :x] = np.array(text_img)

    def CreateTextVideo(self, output_path):
        """创建只显示文本的视频"""
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, self.mask_size)

        for i in range(self.frame_count):
            self.frame = np.zeros((self.mask_size[1], self.mask_size[0], 3), dtype=np.uint8)  # 创建黑色背景
            self.idx = i
            self.DisplayStats()  # 显示时间信息
            out.write(self.frame)  # 写入视频文件

        # 释放资源
        out.release()
        print(f'文本视频已保存到: {output_path}')


if __name__ == '__main__':
    video_path = 'vtest.avi'
    video = VideoMarker(video_path)
    video.Run()  # 运行视频播放器

    # 创建文本视频
    video.CreateTextVideo('text_video.mp4')
