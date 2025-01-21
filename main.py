import os
import json
import time
import queue
import threading
import base64
from datetime import datetime
os.system('reset')
import pyautogui
import numpy as np
from PIL import Image, ImageDraw
import google.generativeai as genai

from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QEventLoop
from PyQt5.QtGui import QPainter, QColor, QPen
from llm_dialog_manager import Agent
from action_executor import ActionExecutor
from region_selector import RegionSelector
from vimium_controller import VimiumController

def main():

    print("\nVimium 自动化控制器")
    print("==========================")
    print("命令列表:")
    print("- 输入 'pause' 暂停自动化")
    print("- 输入 'resume' 恢复自动化")
    print("- 输入 'quit' 退出程序")
    print("- 输入其他内容将发送命令到Gemini")
    # import pdb; pdb.set_trace()
    user_input = input("\n请输入命令: ")
    controller = VimiumController(user_input)
    result = controller.handle_user_input(user_input)


    while True:
        try:
            user_input = input("\n请输入命令: ")
            result = controller.handle_user_input(user_input)
            print(result)

            if result == "正在关闭...":
                break

        except KeyboardInterrupt:
            print("\n强制关闭中...")
            controller.executor.stop()
            break

    controller.executor.join()

if __name__ == "__main__":
    main()
