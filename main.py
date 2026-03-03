import json

import cv2
import pyautogui
import pyperclip
import pygetwindow
import os
import time
import AI.AI

from PIL import ImageGrab
from typing import List, Dict, Any, Tuple
from Ocr.Ocr import createRequest


# 查找图片在模板中的位置，返回中心点坐标
def find_img(target_path, source_path):
    target = cv2.imread(target_path)
    template = cv2.imread(source_path)
    result = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return max_loc[0] + target.shape[1] / 2, max_loc[1] + target.shape[0] / 2


# 打开微信并使其最大化
def open_wechat():
    pyautogui.hotkey('win', 'd')
    file = os.popen(wechat_path)
    file.close()
    wechat_window.maximize()


# 截图整个窗口并保存
def screenshot():
    x1 = wechat_window.left
    y1 = wechat_window.top
    x2 = wechat_window.left + wechat_window.width
    y2 = wechat_window.top + wechat_window.height
    template = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    if template:
        template.save(path + '/image/' + 'template.png')


# 搜索目标
def search_target():
    coord = find_img(searchBox_path, template_path)
    pyautogui.click(coord)
    pyperclip.copy(target_nickname)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.press('enter')


# 截图微信聊天区域并保存
def get_chat_frame():
    x1 = wechat_window.left + 270
    y1 = wechat_window.top + 70
    x2 = wechat_window.left + wechat_window.width
    y2 = wechat_window.top + wechat_window.height - 150
    chat_frame = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    if chat_frame:
        chat_frame.save(path + '/image/' + 'chatFrame.png')


# PCR获取聊天框中的消息
def get_message():
    data_str = createRequest(chatFrame_path)
    data = json.loads(data_str)
    extracted_data = extract_boundingbox_and_text(data)
    classified_data = classify_messages(extracted_data)

    for item in classified_data:
        type_desc = {
            1: "己方消息",
            2: "对方消息",
            3: "其他消息"
        }.get(item['type'], "未知")
        print(f"{type_desc}: {item['text']}")

    if classified_data[-1]['type'] == 2:
        reply_content = ai.get_ai_reply(classified_data)
        send_message(reply_content)
    else:
        print('对方暂时没有发送新消息')


# 从OCR识别结果中提取坐标(boundingBox)和文本(text)
def extract_boundingbox_and_text(data):
    results = []
    regions = data.get('Result', {}).get('regions', [])
    for region in regions:
        lines = region.get('lines', [])
        for line in lines:
            boundingBox = line.get('boundingBox', '')
            text = line.get('text', '')
            if boundingBox and text:
                results.append({
                    'boundingBox': boundingBox,
                    'text': text
                })

    return results


# 解析boundingBox字符串，返回用于比较的坐标
def parse_bounding_box(bounding_box: str) -> tuple:
    coords = [int(coord) for coord in bounding_box.split(',')]
    x1 = coords[0]  # 左上角x坐标
    x2 = coords[2]  # 右上角x坐标

    return x1, x2


# 根据坐标分类消息
def classify_messages(data: List[Dict[str, Any]], tolerance: int = 200) -> List[Dict[str, Any]]:
    if not data:
        return data

    # 找出所有x1的最小值和x2的最大值
    x1_values = []
    x2_values = []

    for item in data:
        x1, x2 = parse_bounding_box(item['boundingBox'])
        x1_values.append(x1)
        x2_values.append(x2)

    min_x1 = min(x1_values)
    max_x2 = max(x2_values)

    print(f'用于做比较的坐标值: min_x1: {min_x1}, max_x2: {max_x2}，当前误差阈值: {tolerance}')

    # 分类统计
    stats = {1: 0, 2: 0, 3: 0}

    # 为每条数据添加type字段
    result = []
    for item in data:
        new_item = item.copy()
        x1, x2 = parse_bounding_box(item['boundingBox'])

        # 判断消息类型
        if abs(x2 - max_x2) <= tolerance:
            new_item['type'] = 1  # 己方消息
            stats[1] += 1
        elif abs(x1 - min_x1) <= tolerance:
            new_item['type'] = 2  # 对方消息
            stats[2] += 1
        else:
            new_item['type'] = 3  # 其他消息
            stats[3] += 1

        result.append(new_item)

    return result


# 发送消息
def send_message(message):
    coord = find_img(dialogBox_path, template_path)
    pyautogui.click(coord)
    pyperclip.copy(message)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.press('enter')


# 主函数
def main():
    open_wechat()
    time.sleep(1)
    screenshot()
    search_target()
    time.sleep(1)
    get_chat_frame()
    get_message()


if __name__ == "__main__":
    wechat_path = 'D:\\Weixin\\Weixin.exe'
    wechat_window = pygetwindow.getWindowsWithTitle('微信')[0]
    target_nickname = '文件传输助手'
    path = os.getcwd().replace('\\', '/')
    template_path = path + '/image/' + 'template.png'
    searchBox_path = path + '/image/' + 'searchBox.png'
    dialogBox_path = path + '/image/' + 'dialogBox.png'
    chatFrame_path = path + '/image/' + 'chatFrame.png'
    ai = AI.AI.DeepSeekBot()
    main()
