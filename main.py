import json
import easyocr
import cv2
import pyautogui
import time
from datetime import datetime
import requests
import torch
import multiprocessing
from itertools import combinations
import os

# 初始化EasyOCR读取器，仅初始化一次
reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)

def take_screenshot():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot = pyautogui.screenshot()
    image_path = f"screenshot_{current_time}.png"
    screenshot.save(image_path)
    print(f"截图已保存为 {image_path}")
    return image_path

def find_partial_text(image, partial_target):
    results = reader.readtext(image)
    for (bbox, text, prob) in results:
        if partial_target.lower() in text.lower():
            (tl, tr, br, bl) = bbox
            tl = (int(tl[0]), int(tl[1]))
            br = (int(br[0]), int(br[1]))
            print(f"Found '{partial_target}' at position: {tl} (top-left), {br} (bottom-right)")
            return tl, br
    return None, None

def generate_combinations(target_string, max_comb_length=5):
    combinations_set = set()
    for length in range(1, max_comb_length + 1):
        for combo in combinations(target_string, length):
            combinations_set.add(''.join(combo))
    return combinations_set

def find_text_coordinates(image_path, target_string, timeout=15):
    image = cv2.imread(image_path)
    image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)

    partial_targets = generate_combinations(target_string)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        manager = multiprocessing.Manager()
        results = manager.list()
        start_time = time.time()

        def search_partial(partial):
            if time.time() - start_time < timeout:
                top_left, bottom_right = find_partial_text(image, partial)
                if top_left and bottom_right:
                    results.append((top_left, bottom_right))
                    pool.terminate()  # 立即停止其他进程

        pool.map_async(search_partial, partial_targets)
        pool.close()
        pool.join()

        if results:
            return results[0][0], results[0][1], image

    print(f"Error: '{target_string}' not found in the image.")
    return None, None, image

def perform_action(top_left, bottom_right, action_type, action_content):
    x = (top_left[0] + bottom_right[0]) // 2
    y = (top_left[1] + bottom_right[1]) // 2

    if action_type == "click":
        pyautogui.click((x, y))
    elif action_type == "type_and_enter":
        pyautogui.click((x, y))
        time.sleep(0.5)
        pyautogui.typewrite(action_content)
        pyautogui.press('enter')
    time.sleep(0.5)

def execute_actions(actions, image_path, debug_mode=False):
    coordinates = None
    image = None
    start_time = time.time()

    for action_data in actions:
        if time.time() - start_time > 15:
            print("操作超时（15秒）。开始新的操作。")
            return False

        action_type = action_data.get('action')
        action_content = action_data.get('content')

        if action_type == 'find':
            top_left, bottom_right, image = find_text_coordinates(image_path, action_content)
            coordinates = (top_left, bottom_right)
            if not coordinates[0]:
                print(f"无法在屏幕上找到目标文本 '{action_content}'")
                return False
        else:
            if not coordinates or not coordinates[0]:
                print("Error: No target coordinates found. Use 'find' action first.")
                return False
            perform_action(coordinates[0], coordinates[1], action_type, action_content)

    return True

def send_to_local_ai(session_id, model_name, prompt):
    LOCAL_API_URL = 'http://127.0.0.1:5000/chat'
    payload = {"session_id": session_id, "model": model_name, "message": prompt}
    try:
        response = requests.post(LOCAL_API_URL, json=payload)
        if response.status_code == 200:
            return response.json().get("response")
        else:
            print(f"Error from AI API: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to AI API: {e}")
    return None

def process_ai_request(prompt):
    import random
    string_rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5))
    session_id = f"user_session_{int(time.time())}_{string_rand}"
    model_name = "claude-3-5-sonnet@20240620"
    return send_to_local_ai(session_id, model_name, prompt)

def main():
    debug_mode = input("是否进入调试模式？(y/n): ").lower() == 'y'
    print(f"调试模式: {'开启' if debug_mode else '关闭'}")

    while True:
        user_input = input("请输入命令（输入 'quit' 退出）: ")
        if user_input.lower() == 'quit':
            break

        while True:
            image_path = take_screenshot()

            prompts = [
                f"Based on the following user input, determine if a screen action is needed. Reply only with 'yes' or 'no'.\nUser input: \"{user_input}\"",
                f"From the following user input, identify the keyword or target text that needs to be found on the screen. Reply only with the text.\nUser input: \"{user_input}\"",
                f"""Based on the following user input, determine the actions to be performed on the screen.
    Reply with a JSON array containing objects. Each object should have two keys: 'action' and 'content'.
    The 'action' key should be one of: 'click', 'double_click', 'type', 'type_and_enter', or 'find'.
    The 'content' key should contain any text to be typed or found, or be null for click actions.

    You will ONLY reply valid JSON format without any additional text.

    For example:
    [
        {{"action": "find", "content": "Search bar"}},
        {{"action": "click", "content": null}},
        {{"action": "type_and_enter", "content": "Python programming"}},
        {{"action": "find", "content": "Results"}},
        {{"action": "click", "content": null}}
    ]

    User input: "{user_input}"
    """
    ]
            with multiprocessing.Pool(processes=3) as pool:
                results = pool.map(process_ai_request, prompts)

            screen_action_response, target_text, action_response = results

            print("AI分析结果 - 是否操作屏幕:", screen_action_response)
            print("AI分析结果 - 目标文本:", target_text)
            print("AI分析结果 - 采取的操作:", action_response)

            if screen_action_response.lower() == "yes":
                try:
                    actions = json.loads(action_response)
                    if not isinstance(actions, list):
                        raise ValueError("Expected a JSON array")
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error: {str(e)}")
                    continue

                if execute_actions(actions, image_path, debug_mode):
                    print("操作完成。是否继续相同的操作？(y/n)")
                    continue_same = input().lower()
                    if continue_same != 'y':
                        break
                else:
                    print("操作未完成。开始新的操作。")
                    break
            else:
                print("无需屏幕操作。")
                break

if __name__ == "__main__":
    main()
