
import queue
from datetime import datetime
import json
import base64
from PIL import Image, ImageDraw
import numpy as np
import pyautogui
from PyQt5.QtCore import QEventLoop
from PyQt5.QtWidgets import QApplication
from constants import VIMIUM_SYSTEM_PROMPT
from action_executor import ActionExecutor
from region_selector import RegionSelector
from llm_dialog_manager import Agent

class VimiumController:
    """Vimium控制器，负责与自定义Agent交互并管理自动化动作"""
    def __init__(self, user_task):
        self.user_task = user_task
        self.setup_agent()
        self.action_queue = queue.Queue()
        self.executor = ActionExecutor(self.action_queue, self)
        self.executor.start()

        # 初始化QApplication
        self.app = QApplication.instance() or QApplication([])

        # 创建事件循环
        self.loop = QEventLoop()

        # 初始化截图区域
        self.selected_region = None
        selector = RegionSelector()

        # 连接选择完成信号
        selector.selection_completed.connect(self.handle_selection_completed)
        selector.show()

        # 等待选择完成
        self.loop.exec_()

        if not self.selected_region:
            print("警告: 未选择区域，使用全屏")
            screen = self.app.desktop().screenGeometry()
            self.selected_region = (0, 0, screen.width(), screen.height())

    def setup_agent(self):
        """初始化Agent"""
        # 选择一个模型，例如 gemini-2.0-flash-exp "claude-2.1"
        self.agent = Agent("gemini-1.5-pro-openai", VIMIUM_SYSTEM_PROMPT+f"\nPlease make sure you are following the user task to get things done: {self.user_task}", memory_enabled=True)

    def handle_selection_completed(self, region):
        """处理选择完成的截图区域"""
        self.selected_region = region
        self.loop.quit()

    def print_response(self, response_text):
        """打印格式化的Agent响应"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] AI 响应:")
        print("=" * 50)
        try:
            # 尝试解析并美化打印JSON
            parsed = self.clean_and_parse_json(response_text)
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except:
            # 如果不是JSON，则原样打印
            print(response_text)
        print("=" * 50 + "\n")

    def take_screenshot(self):
        """截取选定区域的屏幕截图并保存"""
        try:
            timestamp = datetime.now().strftime("%B %d, %Y - %I:%M%p")
            filename = f"Image_{timestamp}.png"

            # 截取选定区域的屏幕截图
            screenshot = pyautogui.screenshot(region=self.selected_region)

            # 转换为PIL图像以进行调整大小
            image = Image.fromarray(np.array(screenshot))

            # 计算新尺寸（原始尺寸的50%）
            width, height = image.size
            new_width = width // 2
            new_height = height // 2

            # 使用LANCZOS重采样进行高质量调整
            resized_image = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

            # 添加边框以显示选择区域
            draw = ImageDraw.Draw(resized_image)
            draw.rectangle([(0, 0), (new_width-1, new_height-1)],
                         outline='red', width=2)

            # 使用最大PNG压缩保存
            resized_image.save(
                filename,
                "PNG",
                optimize=True,
                quality=95
            )

            return filename
        except Exception as e:
            print(f"截图失败: {e}")
            return None

    def upload_to_agent(self, path):
        """上传文件到Agent并获取其URI或路径（假设Agent支持上传）"""
        try:
            # 假设Agent有一个方法来处理文件上传，并返回一个引用
            # 如果没有，需要修改Agent类以支持文件上传
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            file_uri = f"data:image/png;base64,{encoded}"
            return file_uri
        except Exception as e:
            print(f"上传失败: {e}")
            return None

    def analyze_screen(self, screenshot_path):
        """使用Agent分析截图并排队动作"""
        try:
            # 上传截图到Agent
            uploaded_file = self.upload_to_agent(screenshot_path)
            if not uploaded_file:
                print("上传截图到Agent失败。")
                return

            # 准备包含上传文件的消息
            prompt = "基于此截图，我们应采取哪些下一步操作？请考虑可见的Vimium提示，并以JSON格式返回下一个动作，注意如果是VIM的mode，观察黄色的提示，可以是两个字母也可以是一个字母。"

            # 添加消息到Agent
            self.agent.add_message("user", prompt)
            self.agent.add_image(screenshot_path)

            # 生成响应
            response = self.agent.generate_response(json_format=True, temperature=1,top_p=0.95,top_k=40,max_tokens=8096)

            # 打印响应
            self.print_response(response)
            from llm_dialog_manager import ChatHistory
            history = self.agent.history[:]
            image = history.pop(-2)
            print(image)
            self.agent.history = ChatHistory(history)

            # 解析并入队动作
            self.process_agent_response(response)

        except Exception as e:
            print(f"分析截图失败: {e}")
            print(f"错误详情: {str(e)}")


    def clean_and_parse_json(self, response_text):
        """
        清理和解析可能包含Markdown或其他格式的JSON响应
        """
        def strip_markdown_blocks(text):
            # 首先移除字符串两端的空白字符
            text = text.strip()

            # 更健壮的方式处理markdown代码块
            if text.startswith('```'):
                # 找到第一个换行符
                first_newline = text.find('\n')
                if first_newline != -1:
                    text = text[first_newline:].strip()

            # 处理尾部的markdown标记
            if text.endswith('```'):
                # 找到最后一个换行符
                last_newline = text.rfind('\n')
                if last_newline != -1:
                    text = text[:last_newline].strip()

            # 移除任何剩余的反引号
            text = text.strip('`')

            # 确保返回的文本是清理过的
            return text.strip()

        def remove_comments(text):
            # 移除JSON中的注释（如果有）
            import re
            text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)  # 移除单行注释
            text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)  # 移除多行注释
            return text

        def fix_trailing_commas(text):
            # 修复尾随逗号
            import re
            text = re.sub(r',(\s*[}\]])', r'\1', text)
            return text

        def clean_control_characters(text):
            # 清理可能导致JSON解析失败的控制字符
            if isinstance(text, str):
                return ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
            return text

        try:
            # 首先尝试直接解析
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 如果失败，进行清理后重试
            cleaned_text = response_text
            # 应用所有清理步骤
            cleaned_text = strip_markdown_blocks(cleaned_text)
            cleaned_text = remove_comments(cleaned_text)
            cleaned_text = fix_trailing_commas(cleaned_text)
            cleaned_text = clean_control_characters(cleaned_text)

            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                # 如果仍然失败，提供更详细的错误信息
                print(f"清理后的文本仍然无法解析为JSON:")
                print(f"清理后的文本:\n{cleaned_text}")
                print(f"错误位置: 行 {e.lineno}, 列 {e.colno}")
                print(f"错误信息: {e.msg}")
                raise

    def process_agent_response(self, response_text):
        """处理Agent的响应并将动作入队"""
        try:
            actions = self.clean_and_parse_json(response_text)
            if isinstance(actions, list):
                # Queue each action in the list
                for action in actions:
                    self.action_queue.put(action)
            else:
                # If it's a single action, queue it directly
                self.action_queue.put(actions)
        except json.JSONDecodeError as e:
            print(f"解析AI响应失败: {e}")
            print(f"响应内容: {response_text}")

    def handle_user_input(self, user_input):
        """在自动化过程中处理用户输入"""
        if user_input.lower() == "pause":
            self.executor.pause()
            return "自动化已暂停。输入 'resume' 以继续。"

        elif user_input.lower() == "resume":
            self.executor.resume()
            return "自动化已恢复。"

        elif user_input.lower() == "quit":
            self.executor.stop()
            return "正在关闭..."

        else:
            # 将用户输入发送给Agent进行分析
            try:
                prompt = f"用户的请求: {user_input}\n请以JSON格式提供实现此操作的**第一个**步骤。" # 注意这里强调了第一个步骤
                self.agent.add_message("user", prompt)
                # 生成响应
                response = self.agent.generate_response(temperature=1,top_p=0.95,top_k=40,max_tokens=8096,json_format=True)
                print(self.agent.history)

                # 打印响应
                self.print_response(response)

                # 解析并入队动作
                self.process_agent_response(response)

                return "动作已入队。输入 'pause' 以暂停执行。"
            except Exception as e:
                return f"处理输入时出错: {e}"

    def __del__(self):
        """在对象删除时清理线程"""
        if hasattr(self, 'executor'):
            self.executor.stop()
