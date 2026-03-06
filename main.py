import json
import cv2
import keyboard
import pyautogui
import pyperclip
import pygetwindow
import os
import time
import AI.AI
import sys
from datetime import datetime
from PIL import ImageGrab
from typing import List, Dict, Any, Tuple
from Ocr.Ocr import createRequest


class WeChatBot:
    """
    一个用于自动化微信操作的机器人。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化机器人。

        :param config: 包含配置信息的字典。
        """
        self.config = config
        self.wechat_window = self._get_wechat_window()

        # 路径设置
        self.base_path = os.getcwd().replace('\\', '/')
        self.image_path = os.path.join(self.base_path, 'image')
        os.makedirs(self.image_path, exist_ok=True)

        self.image_paths = {
            'template': os.path.join(self.image_path, 'template.png'),
            'searchBox': os.path.join(self.image_path, 'searchBox.png'),
            'dialogBox': os.path.join(self.image_path, 'dialogBox.png'),
            'chatFrame': os.path.join(self.image_path, 'chatFrame.png'),
        }

        self.ai = AI.AI.DeepSeekBot()

    @staticmethod
    def _get_wechat_window():
        """获取微信窗口对象，如果找不到则退出程序。"""
        try:
            return pygetwindow.getWindowsWithTitle('微信')[0]
        except IndexError:
            print("错误：未找到微信窗口。请确保微信已打开。")
            sys.exit(1)

    @staticmethod
    def find_img(target_path: str, source_path: str) -> Tuple[float, float]:
        """查找图片在模板中的位置，返回中心点坐标。"""
        target = cv2.imread(target_path)
        template = cv2.imread(source_path)
        result = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        return max_loc[0] + target.shape[1] / 2, max_loc[1] + target.shape[0] / 2

    def open_wechat(self):
        """打开微信并使其最大化。"""
        pyautogui.hotkey('win', 'd')
        with os.popen(self.config['wechat_path']) as f:
            pass
        self.wechat_window.maximize()

    def screenshot(self):
        """截图整个窗口并保存。"""
        x1, y1 = self.wechat_window.left, self.wechat_window.top
        x2, y2 = x1 + self.wechat_window.width, y1 + self.wechat_window.height
        template = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        template.save(self.image_paths['template'])

    def search_target(self):
        """搜索目标联系人或群聊。"""
        coord = self.find_img(self.image_paths['searchBox'], self.image_paths['template'])
        pyautogui.click(coord)
        pyperclip.copy(self.config['target_nickname'])
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')

    def get_chat_frame(self):
        """截图微信聊天区域并保存。"""
        x1 = self.wechat_window.left + 270
        y1 = self.wechat_window.top + 70
        x2 = self.wechat_window.left + self.wechat_window.width
        y2 = self.wechat_window.top + self.wechat_window.height - 150
        chat_frame = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        chat_frame.save(self.image_paths['chatFrame'])

    def get_message(self):
        """OCR获取聊天框中的消息并根据情况回复。"""
        data_str = createRequest(self.image_paths['chatFrame'])
        data = json.loads(data_str)
        extracted_data = self.extract_boundingbox_and_text(data)
        classified_data = self.classify_messages(extracted_data)

        if not classified_data:
            print("未识别到任何消息。")
            return

        for item in classified_data:
            type_desc = {1: "己方消息", 2: "对方消息", 3: "其他消息"}.get(item['type'], "未知")
            print(f"{type_desc}: {item['text']}")

        last_message = classified_data[-1]
        is_group = self.config.get('is_group', False)
        my_name = self.config.get('my_name', '')

        should_reply = False
        if is_group:
            if my_name and my_name in last_message['text']:
                print(f"群聊中有人 @{my_name}，准备回复...")
                should_reply = True
            else:
                print('群里暂时没有人@你')
        elif last_message['type'] == 2:
            print("收到对方新消息，准备回复...")
            should_reply = True
        else:
            print('对方暂时没有给你发送新消息')

        if should_reply:
            reply_content = self.ai.get_ai_reply(classified_data)
            self.send_message(reply_content)

    @staticmethod
    def extract_boundingbox_and_text(data: Dict[str, Any]) -> List[Dict[str, str]]:
        """从OCR识别结果中提取坐标(boundingBox)和文本(text)。"""
        results = []
        regions = data.get('Result', {}).get('regions', [])
        for region in regions:
            for line in region.get('lines', []):
                if 'boundingBox' in line and 'text' in line:
                    results.append({'boundingBox': line['boundingBox'], 'text': line['text']})
        return results

    @staticmethod
    def parse_bounding_box(bounding_box: str) -> Tuple[int, int]:
        """解析boundingBox字符串，返回用于比较的坐标。"""
        coords = [int(coord) for coord in bounding_box.split(',')]
        return coords[0], coords[2]  # x1, x2

    def classify_messages(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据坐标分类消息。"""
        if not data:
            return []

        x1_values, x2_values = [], []
        for item in data:
            x1, x2 = self.parse_bounding_box(item['boundingBox'])
            x1_values.append(x1)
            x2_values.append(x2)

        min_x1, max_x2 = min(x1_values), max(x2_values)
        tolerance = self.config.get('message_box_tolerance', 200)
        print(f'用于做比较的坐标值: min_x1: {min_x1}, max_x2: {max_x2}，当前误差阈值: {tolerance}')

        result = []
        for item in data:
            new_item = item.copy()
            x1, x2 = self.parse_bounding_box(item['boundingBox'])
            if abs(x2 - max_x2) <= tolerance:
                new_item['type'] = 1  # 己方消息
            elif abs(x1 - min_x1) <= tolerance:
                new_item['type'] = 2  # 对方消息
            else:
                new_item['type'] = 3  # 其他消息
            result.append(new_item)
        return result

    def send_message(self, message: str):
        """发送消息。"""
        coord = self.find_img(self.image_paths['dialogBox'], self.image_paths['template'])
        pyautogui.click(coord)
        pyperclip.copy(message)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')

    def run_timer_task(self, interval: int):
        """定时任务。"""
        print(f"定时任务启动（间隔{interval}秒），按 ctrl+1 组合键退出")
        print("=" * 50)

        while True:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始执行任务")
                self.get_chat_frame()
                self.get_message()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 任务完成")

                for i in range(interval, 0, -1):
                    if keyboard.is_pressed('ctrl+1'):
                        raise KeyboardInterrupt
                    print(f"距离下次执行还有 {i:2d} 秒", end='\r')
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n程序已安全退出")
                sys.exit(0)

    def run(self):
        """启动机器人的主流程。"""
        self.open_wechat()
        time.sleep(1)
        self.screenshot()
        self.search_target()
        time.sleep(1)
        self.run_timer_task(self.config.get('interval', 10))


def main():
    """
    主函数，配置并启动机器人。
    """
    config = {
        'wechat_path': 'D:\\Weixin\\Weixin.exe',
        'target_nickname': '用于搜索聊天或群聊的名称',
        'my_name': "@谷雨",
        'is_group': True,
        'interval': 10,
        'message_box_tolerance': 200,
    }
    bot = WeChatBot(config)
    bot.run()


if __name__ == "__main__":
    main()
