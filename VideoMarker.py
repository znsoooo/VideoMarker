import csv
import cv2
import numpy as np


class VideoPlayer:
    def __init__(self, video_path):
        self.video_path = video_path

        # 初始化视频捕获对象
        self.cap = cv2.VideoCapture(video_path)

        # 检查视频是否成功打开
        if not self.cap.isOpened():
            print(f'无法打开视频文件: {video_path}')
            exit()

        # 获取视频属性
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame = self.cap.read()[1]

        # 初始化变量
        self.idx = 0
        self.paused = False

        # 计时统计
        self.time_stat = []

        # 文本显示位置
        self.text_pos = (10, 30)
        self.stats_pos = (10, 60)

    def MoveFrame(self, count=1):
        """向后移动指定帧数"""
        new_idx = max(0, min(self.frame_count - 1, self.idx + count))
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
        key = cv2.waitKeyEx(int(1000 / self.fps))

        if key == 27:  # ESC键退出
            return False

        elif key == ord(' '):  # 空格键：暂停/继续
            self.paused = not self.paused

        elif key == 0x250000:  # 左箭头
            return self.MoveFrame(-1 if self.paused else int(-5 * self.fps))

        elif key == 0x270000:  # 右箭头
            return self.MoveFrame(1 if self.paused else int(5 * self.fps))

        elif key in [ord('1'), ord('2'), ord('3')]:
            # 记录当前时间点
            group_id = key - ord('0')
            self.time_stat.append((self.idx, group_id))
            self.time_stat.sort()
            self.SaveCsvFile()

        return self.MoveFrame(not self.paused)

    def Run(self):
        """视频播放主循环"""
        while self.GetNextFrame():
            self.DisplayStats()
            cv2.imshow('Video Player', self.frame)

        # 释放资源
        self.cap.release()
        cv2.destroyAllWindows()

    def FormatTime(self, frames):
        """将帧数转换为时间字符串 (HH:MM:SS.NNN)"""
        seconds = frames / self.fps
        seconds_int = int(seconds)
        minutes, secs = divmod(seconds_int, 60)
        ms = int((seconds - seconds_int) * 1000)
        return f'{minutes:02d}:{secs:02d}.{ms:03d}'

    def FormatStatTexts(self):
        """更新计时统计"""
        if not self.time_stat:
            return []

        # 计算时长统计
        self.time_stat.sort()
        stat = [0, 0, 0]
        for (idx_last, group_id), (idx, _) in zip(self.time_stat, self.time_stat[1:] + [(self.idx, -1)]):
            if idx > self.idx:
                stat[group_id - 1] += self.idx - idx_last
                break
            else:
                stat[group_id - 1] += idx - idx_last

        # 计算时长统计百分比
        stat_texts = []
        total = self.idx - self.time_stat[0][0] or 1
        for i, frames in enumerate(stat):
            if frames > 0:
                stat_text = f'Status {i + 1}: {self.FormatTime(frames)} ({frames / total: .2%})'
                stat_texts.append(stat_text)

        return stat_texts

    def DisplayStats(self):
        """在屏幕上显示时间信息"""
        time_text = f'{self.FormatTime(self.idx)}/{self.FormatTime(self.frame_count - 1)}'
        cv2.putText(self.frame, time_text, self.text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 在屏幕上显示各状态的统计时长
        for i, stats_text in enumerate(self.FormatStatTexts()):
            cv2.putText(self.frame, stats_text, (self.stats_pos[0], self.stats_pos[1] + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    def SaveCsvFile(self):
        """保存到CSV文件"""
        with open('groups.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['帧序号', '组别'])
            writer.writerows(self.time_stat)

    def CreateTextVideo(self, output_path):
        """创建只显示文本的视频"""
        width, height = (600, 400)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))

        for i in range(self.frame_count):
            self.frame = np.zeros((height, width, 3), dtype=np.uint8)  # 创建黑色背景
            self.idx = i
            self.DisplayStats()  # 显示时间信息
            out.write(self.frame)  # 写入视频文件

        # 释放资源
        out.release()
        print(f'文本视频已保存到: {output_path}')


if __name__ == '__main__':
    video_path = 'vtest.avi'
    player = VideoPlayer(video_path)
    player.Run()  # 运行视频播放器

    # 创建文本视频
    player.CreateTextVideo('text_video.mp4')
