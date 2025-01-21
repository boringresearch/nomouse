
import threading
import queue
import time
import pyautogui
from constants import SPECIAL_KEYS

class ActionExecutor(threading.Thread):
    def __init__(self, action_queue, gemini_controller):
        super().__init__()
        self.action_queue = action_queue
        self.gemini_controller = gemini_controller
        self.running = True
        self.paused = False
        self.pause_condition = threading.Condition()

    def run(self):
        while self.running:
            with self.pause_condition:
                while self.paused and self.running:
                    self.pause_condition.wait()

            try:
                action = self.action_queue.get(timeout=1)
                if action is None:
                    continue

                self.execute_action(action)
                self.action_queue.task_done()

            except queue.Empty:
                continue

    def execute_action(self, action):
        """执行单个动作"""
        action_type = action["action"]["type"]
        step = action.get("step", "unknown")
        print(f"Executing step {step}: {action_type}")

        if action_type == "vim_key":
            keys = action["action"]["key"].split(",")  # 分割成列表
            print(f"Pressing keys: {keys}")

            for key in keys:  # 遍历每个key
                key = key.strip()  # 去除可能的空格
                if key.lower() in SPECIAL_KEYS:
                    pyautogui.press(key.lower())
                else:
                    for k in key:
                        pyautogui.press(k)
                        print(f"Pressed key: {k}")
                        time.sleep(1)
                time.sleep(0.5)

            self.gemini_controller.analyze_screen(self.gemini_controller.take_screenshot())

        elif action_type == "type":
            text = action["action"]["text"]
            print(f"Typing text: {text}")
            time.sleep(1)  # 等待输入框完全聚焦

            # 清理已有内容
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')

            # 使用 typewrite 而不是 write
            pyautogui.typewrite(text)
            time.sleep(0.5)

            self.gemini_controller.analyze_screen(self.gemini_controller.take_screenshot())

        elif action_type == "wait":
            time.sleep(1)  # 等待视觉反馈
            # 执行完 wait 后，进行分析
            self.gemini_controller.analyze_screen(self.gemini_controller.take_screenshot())

        elif action_type == "analyze":
            screenshot = self.gemini_controller.take_screenshot()
            if screenshot:
                self.gemini_controller.analyze_screen(screenshot)

        elif action_type == "done":
            print("任务完成。")
            self.gemini_controller.agent.save_conversation()
            self.stop()

    def pause(self):
        """暂停动作执行"""
        self.paused = True

    def resume(self):
        """恢复动作执行"""
        with self.pause_condition:
            self.paused = False
            self.pause_condition.notify()

    def stop(self):
        """停止执行器线程"""
        self.running = False
        with self.pause_condition:
            self.pause_condition.notify()
