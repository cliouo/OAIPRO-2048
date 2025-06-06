# 2048游戏自动化脚本主文件
import asyncio
import time
import threading
import logging
from typing import Dict, Any, Optional
from DrissionPage import ChromiumPage, ChromiumOptions
from game_ai import Game2048AI
from websocket_handler import WebSocketHandler
from config import *

class Game2048AutoPlayer:
    def __init__(self):
        self.page = None
        self.ai = Game2048AI()
        self.websocket_handler = None
        self.is_auto_playing = False
        self.current_board = None
        self.current_score = 0
        self.game_over = False
        self.victory = False
        self.awaiting_response = False
        self.last_board_hash = None
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # WebSocket事件循环
        self.loop = None
        self.websocket_thread = None
    
    def setup_browser(self):
        """设置浏览器"""
        try:
            # 配置浏览器选项
            options = ChromiumOptions()
            if BROWSER_HEADLESS:
                options.headless()
            
            # 启动浏览器
            self.page = ChromiumPage(options)
            self.page.set.timeouts(BROWSER_TIMEOUT)
            
            self.logger.info("浏览器启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"浏览器启动失败: {e}")
            return False
    
    def load_game_page(self):
        """加载游戏页面"""
        try:
            self.logger.info(f"正在加载游戏页面: {GAME_URL}")

            # 开始监听WebSocket连接
            self.page.listen.start('ws', is_regex=False)
            self.logger.info("开始监听WebSocket连接...")

            self.page.get(GAME_URL)

            # 等待页面加载完成
            time.sleep(3)

            # 检查页面是否加载成功
            if "2048" in self.page.title:
                self.logger.info("游戏页面加载成功")
                return True
            else:
                self.logger.error("游戏页面加载失败")
                return False

        except Exception as e:
            self.logger.error(f"加载游戏页面失败: {e}")
            return False

    def extract_websocket_token(self):
        """从页面提取WebSocket token"""
        try:
            self.logger.info("正在提取WebSocket token...")

            # 方法1: 从cookies中获取auth_token
            cookies = self.page.cookies()
            for cookie in cookies:
                if cookie.get('name') == 'auth_token':
                    token = cookie.get('value')
                    if token:
                        self.logger.info(f"从cookies获取到auth_token: {token[:20]}...")
                        return token

            # 方法2: 从页面JavaScript变量中获取
            token = self.page.run_js("""
                // 尝试从cookies获取auth_token
                function getCookie(name) {
                    const value = `; ${document.cookie}`;
                    const parts = value.split(`; ${name}=`);
                    if (parts.length === 2) return parts.pop().split(';').shift();
                    return null;
                }

                const authToken = getCookie('auth_token');
                if (authToken) return authToken;

                // 尝试从全局变量获取token
                if (window.wsToken) return window.wsToken;
                if (window.token) return window.token;
                if (window.authToken) return window.authToken;

                // 尝试从localStorage获取
                if (localStorage.getItem('token')) return localStorage.getItem('token');
                if (localStorage.getItem('authToken')) return localStorage.getItem('authToken');
                if (localStorage.getItem('auth_token')) return localStorage.getItem('auth_token');
                if (localStorage.getItem('wsToken')) return localStorage.getItem('wsToken');

                // 尝试从sessionStorage获取
                if (sessionStorage.getItem('token')) return sessionStorage.getItem('token');
                if (sessionStorage.getItem('authToken')) return sessionStorage.getItem('authToken');
                if (sessionStorage.getItem('auth_token')) return sessionStorage.getItem('auth_token');

                return null;
            """)

            if token:
                self.logger.info(f"从JavaScript获取到token: {token[:20]}...")
                return token

            # 方法3: 从页面源码中提取
            page_source = self.page.html
            import re

            # 查找token模式
            token_patterns = [
                r'auth_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'wsToken["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'authToken["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'ws\?token=([^"\'&\s]+)',
                r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',  # JWT格式
            ]

            for pattern in token_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    token = matches[0]
                    self.logger.info(f"从页面源码获取到token: {token[:20]}...")
                    return token

            self.logger.warning("无法自动获取token，请手动设置")
            return None

        except Exception as e:
            self.logger.error(f"提取WebSocket token失败: {e}")
            return None
    
    def inject_control_button(self):
        """注入控制按钮"""
        try:
            # 注入CSS样式
            css_code = """
            <style>
            #auto-play-controls {
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 9999;
                background: rgba(255, 255, 255, 0.9);
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
            }
            
            .control-button {
                display: block;
                width: 120px;
                padding: 8px 12px;
                margin: 5px 0;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
                transition: background-color 0.3s;
            }
            
            #start-auto-btn {
                background-color: #4CAF50;
                color: white;
            }
            
            #start-auto-btn:hover {
                background-color: #45a049;
            }
            
            #stop-auto-btn {
                background-color: #f44336;
                color: white;
            }
            
            #stop-auto-btn:hover {
                background-color: #da190b;
            }
            
            #status-display {
                font-size: 12px;
                margin-top: 10px;
                padding: 5px;
                background: #f0f0f0;
                border-radius: 3px;
            }
            </style>
            """
            
            # 注入HTML控制面板
            html_code = """
            <div id="auto-play-controls">
                <button id="start-auto-btn" class="control-button">开始自动游戏</button>
                <button id="stop-auto-btn" class="control-button" style="display:none;">停止自动游戏</button>
                <button id="set-token-btn" class="control-button" style="background-color: #2196F3;">设置Token</button>
                <div id="status-display">
                    <div>状态: 等待开始</div>
                    <div>分数: 0</div>
                    <div>WebSocket: 未连接</div>
                </div>
            </div>
            """
            
            # 注入JavaScript控制逻辑
            js_code = """
            // 添加样式
            document.head.insertAdjacentHTML('beforeend', arguments[0]);

            // 添加控制面板
            document.body.insertAdjacentHTML('beforeend', arguments[1]);

            // 绑定事件
            document.getElementById('start-auto-btn').onclick = function() {
                window.startAutoPlay = true;
                this.style.display = 'none';
                document.getElementById('stop-auto-btn').style.display = 'block';
                updateStatus('自动游戏中', null, null);
            };

            document.getElementById('stop-auto-btn').onclick = function() {
                window.stopAutoPlay = true;
                this.style.display = 'none';
                document.getElementById('start-auto-btn').style.display = 'block';
                updateStatus('已停止', null, null);
            };

            document.getElementById('set-token-btn').onclick = function() {
                const token = prompt('请输入WebSocket token:', '');
                if (token) {
                    window.newToken = token;
                    updateStatus(null, null, '重新连接中...');
                }
            };

            // 状态更新函数
            window.updateStatus = function(status, score, wsStatus) {
                const statusDiv = document.getElementById('status-display');
                let html = '<div>状态: ' + (status || '等待开始') + '</div>';
                if (score !== null) html += '<div>分数: ' + score + '</div>';
                if (wsStatus !== null) html += '<div>WebSocket: ' + wsStatus + '</div>';
                statusDiv.innerHTML = html;
            };

            // 初始化标志
            window.startAutoPlay = false;
            window.stopAutoPlay = false;
            window.newToken = null;
            """
            
            self.page.run_js(js_code, css_code, html_code)
            self.logger.info("控制按钮注入成功")
            return True
            
        except Exception as e:
            self.logger.error(f"注入控制按钮失败: {e}")
            return False
    
    def extract_websocket_from_network(self):
        """从网络监听中提取WebSocket token"""
        try:
            self.logger.info("尝试从网络监听中获取WebSocket连接...")

            # 首先检查当前cookies中是否有auth_token
            cookies = self.page.cookies()
            for cookie in cookies:
                if cookie.get('name') == 'auth_token':
                    token = cookie.get('value')
                    if token:
                        self.logger.info(f"从当前cookies获取到auth_token: {token[:20]}...")
                        return token

            # 等待WebSocket连接建立
            for packet in self.page.listen.steps(count=10, timeout=5):
                if packet and 'ws' in packet.url.lower():
                    self.logger.info(f"检测到WebSocket连接: {packet.url}")

                    # 从URL中提取token
                    if 'token=' in packet.url:
                        import re
                        token_match = re.search(r'token=([^&\s]+)', packet.url)
                        if token_match:
                            token = token_match.group(1)
                            self.logger.info(f"从网络监听获取到token: {token[:20]}...")
                            return token

                    # 检查请求中的cookies
                    if hasattr(packet, 'request') and packet.request and hasattr(packet.request, 'cookies'):
                        for cookie in packet.request.cookies:
                            if cookie.get('name') == 'auth_token':
                                token = cookie.get('value')
                                if token:
                                    self.logger.info(f"从WebSocket请求cookies获取到auth_token: {token[:20]}...")
                                    return token

            self.logger.info("网络监听中未发现WebSocket连接")
            return None

        except Exception as e:
            self.logger.error(f"从网络监听提取WebSocket token失败: {e}")
            return None

    def setup_websocket(self):
        """设置WebSocket连接"""
        try:
            # 首先尝试从网络监听中获取WebSocket连接
            token = self.extract_websocket_from_network()

            if not token:
                # 如果网络监听没有获取到，尝试传统方法
                token = self.extract_websocket_token()

            if token:
                # 创建WebSocket处理器
                self.websocket_handler = WebSocketHandler(self.on_game_state_received)
                self.websocket_handler.page = self.page  # 设置页面引用
                self.websocket_handler.set_websocket_url(token)

                # 在新线程中运行WebSocket
                self.websocket_thread = threading.Thread(target=self.run_websocket, daemon=True)
                self.websocket_thread.start()

                self.logger.info("WebSocket设置完成")
            else:
                self.logger.warning("无法自动获取WebSocket token，程序将继续运行，可稍后手动设置")

            # 无论是否获取到token都继续运行程序
            return True

        except Exception as e:
            self.logger.error(f"WebSocket设置失败: {e}")
            # 即使WebSocket设置失败也继续运行程序
            return True

    def show_token_input_dialog(self):
        """显示token输入对话框"""
        try:
            js_code = """
            const token = prompt('无法自动获取WebSocket token，请手动输入token:', '');
            if (token) {
                window.manualToken = token;
                return token;
            }
            return null;
            """

            token = self.page.run_js(js_code)
            if token:
                self.logger.info(f"用户手动输入token: {token[:20]}...")

                # 创建WebSocket处理器
                self.websocket_handler = WebSocketHandler(self.on_game_state_received)
                self.websocket_handler.page = self.page  # 设置页面引用
                self.websocket_handler.set_websocket_url(token)

                # 在新线程中运行WebSocket
                self.websocket_thread = threading.Thread(target=self.run_websocket, daemon=True)
                self.websocket_thread.start()

                return True
            else:
                self.logger.warning("用户未输入token，WebSocket功能将不可用")
                return False

        except Exception as e:
            self.logger.error(f"显示token输入对话框失败: {e}")
            return False
    
    def run_websocket(self):
        """在新线程中运行WebSocket"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.websocket_handler.connect())
        except Exception as e:
            self.logger.error(f"WebSocket运行错误: {e}")
    
    async def make_ai_move(self):
        """使用AI计算并执行移动"""
        try:
            if not self.current_board or self.awaiting_response:
                return

            # 使用AI计算最佳移动
            best_move = await self.ai.get_best_move(self.current_board, self.current_score)

            if best_move:
                predicted = self.ai.move_board(self.current_board, best_move)
                if predicted == self.current_board:
                    self.logger.info("AI选择的方向无效，重新计算")
                    return

                self.logger.info(f"AI选择移动方向: {best_move}")

                success = False
                if self.websocket_handler and self.websocket_handler.get_connection_status():
                    success = await self.websocket_handler.send_move(best_move)
                else:
                    self.simulate_keyboard_move(best_move)
                    success = True

                if success:
                    self.awaiting_response = True

                await asyncio.sleep(MOVE_DELAY)
                
        except Exception as e:
            self.logger.error(f"AI移动失败: {e}")
    
    def simulate_keyboard_move(self, direction: str):
        """模拟键盘按键移动"""
        try:
            key_map = {
                "up": "ArrowUp",
                "down": "ArrowDown", 
                "left": "ArrowLeft",
                "right": "ArrowRight"
            }
            
            key = key_map.get(direction)
            if key:
                js_code = f"""
                document.dispatchEvent(new KeyboardEvent('keydown', {{
                    key: '{key}',
                    code: '{key}',
                    keyCode: {{'ArrowUp': 38, 'ArrowDown': 40, 'ArrowLeft': 37, 'ArrowRight': 39}}['{key}']
                }}));
                """
                self.page.run_js(js_code)
                self.logger.info(f"模拟键盘按键: {key}")
                
        except Exception as e:
            self.logger.error(f"模拟键盘按键失败: {e}")
    
    def on_game_state_received(self, game_data: Optional[Dict[str, Any]]):
        """处理接收到的游戏状态或错误"""
        try:
            board_changed = False
            if game_data:
                self.current_board = game_data.get("board", [])
                self.current_score = game_data.get("score", 0)
                self.game_over = game_data.get("game_over", False)
                self.victory = game_data.get("victory", False)

                board_hash = tuple(tuple(row) for row in self.current_board)
                if board_hash != self.last_board_hash:
                    self.last_board_hash = board_hash
                    board_changed = True

            # 更新页面状态显示
            self.update_page_status()

            # 表示已收到上一次移动的响应
            self.awaiting_response = False

            # 检查游戏是否结束
            if self.game_over or self.victory:
                self.logger.info(f"游戏结束 - 胜利: {self.victory}, 失败: {self.game_over}, 最终分数: {self.current_score}")
                self.stop_auto_play()

                # 游戏结束后停止WebSocket重连，避免无限重连
                if self.websocket_handler:
                    self.websocket_handler.should_reconnect = False
                    self.logger.info("游戏结束，停止WebSocket重连")
                return

            # 如果正在自动游戏且游戏未结束，计算下一步
            if self.is_auto_playing and (board_changed or game_data is None):
                asyncio.create_task(self.make_ai_move())

        except Exception as e:
            self.logger.error(f"处理游戏状态失败: {e}")
    
    def update_page_status(self):
        """更新页面状态显示"""
        try:
            ws_status = "已连接" if self.websocket_handler and self.websocket_handler.get_connection_status() else "未连接"
            
            js_code = f"""
            if (window.updateStatus) {{
                window.updateStatus(null, {self.current_score}, '{ws_status}');
            }}
            """
            
            self.page.run_js(js_code)
            
        except Exception as e:
            self.logger.error(f"更新页面状态失败: {e}")
    
    def check_user_controls(self):
        """检查用户控制指令"""
        try:
            # 检查开始指令
            start_flag = self.page.run_js("return window.startAutoPlay;")
            if start_flag:
                self.page.run_js("window.startAutoPlay = false;")
                self.start_auto_play()

            # 检查停止指令
            stop_flag = self.page.run_js("return window.stopAutoPlay;")
            if stop_flag:
                self.page.run_js("window.stopAutoPlay = false;")
                self.stop_auto_play()

            # 检查新token设置
            new_token = self.page.run_js("return window.newToken;")
            if new_token:
                self.page.run_js("window.newToken = null;")
                self.update_websocket_token(new_token)

        except Exception as e:
            # 检查是否是页面连接断开错误
            if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                self.logger.warning("页面连接已断开，停止用户控制检查")
                # 停止自动游戏
                self.is_auto_playing = False
                return False
            else:
                self.logger.error(f"检查用户控制失败: {e}")
        return True

    def check_websocket_connections(self):
        """检查新的WebSocket连接"""
        try:
            # 如果还没有WebSocket连接，继续监听
            if not self.websocket_handler or not self.websocket_handler.get_connection_status():
                # 检查是否有新的WebSocket连接
                try:
                    packet = self.page.listen.wait(count=1, timeout=0.1, fit_count=False)
                    if packet and isinstance(packet, list) and len(packet) > 0:
                        packet = packet[0]

                    if packet and 'ws' in packet.url.lower():
                        self.logger.info(f"检测到新的WebSocket连接: {packet.url}")

                        # 从URL中提取token
                        if 'token=' in packet.url:
                            import re
                            token_match = re.search(r'token=([^&\s]+)', packet.url)
                            if token_match:
                                token = token_match.group(1)
                                self.logger.info(f"从新连接获取到token: {token[:20]}...")
                                self.update_websocket_token(token)
                except Exception as listen_error:
                    # 检查是否是页面连接断开错误
                    if "connection" in str(listen_error).lower() or "disconnect" in str(listen_error).lower():
                        self.logger.warning("页面连接已断开，停止WebSocket监听")
                        # 停止WebSocket相关操作
                        if self.websocket_handler:
                            self.websocket_handler.should_reconnect = False
                        return
                    # 其他错误继续

        except Exception as e:
            # 检查是否是页面连接断开错误
            if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                self.logger.warning("页面连接已断开，停止WebSocket检查")
                if self.websocket_handler:
                    self.websocket_handler.should_reconnect = False
            else:
                self.logger.error(f"检查WebSocket连接失败: {e}")

    def update_websocket_token(self, token: str):
        """更新WebSocket token"""
        try:
            self.logger.info(f"更新WebSocket token: {token[:20]}...")

            # 断开现有连接
            if self.websocket_handler:
                if self.loop and not self.loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self.websocket_handler.disconnect(),
                        self.loop
                    )

            # 等待断开完成
            time.sleep(1)

            # 设置新token并重新连接
            if self.websocket_handler:
                self.websocket_handler.set_websocket_url(token)
                self.websocket_handler.page = self.page  # 确保页面引用存在
                self.websocket_handler.should_reconnect = True

                # 重新启动WebSocket连接
                self.websocket_thread = threading.Thread(target=self.run_websocket, daemon=True)
                self.websocket_thread.start()

                self.logger.info("WebSocket token更新完成")

        except Exception as e:
            self.logger.error(f"更新WebSocket token失败: {e}")
    
    def start_auto_play(self):
        """开始自动游戏"""
        self.is_auto_playing = True
        self.logger.info("开始自动游戏")
    
    def stop_auto_play(self):
        """停止自动游戏"""
        self.is_auto_playing = False
        self.logger.info("停止自动游戏")
    
    def run(self):
        """运行主程序"""
        try:
            self.logger.info("启动2048自动游戏程序")
            
            # 设置浏览器
            if not self.setup_browser():
                return
            
            # 加载游戏页面
            if not self.load_game_page():
                return
            
            # 注入控制按钮
            if not self.inject_control_button():
                return
            
            # 设置WebSocket
            if not self.setup_websocket():
                return
            
            # 主循环
            self.logger.info("程序启动完成，等待用户操作...")

            while True:
                try:
                    # 检查用户控制，如果页面断开则退出
                    if not self.check_user_controls():
                        self.logger.info("页面连接断开，退出主循环")
                        break

                    # 检查新的WebSocket连接
                    self.check_websocket_connections()

                    # 检查游戏结束状态
                    if self.is_auto_playing and (self.game_over or self.victory):
                        self.logger.info(f"游戏结束 - 胜利: {self.victory}, 失败: {self.game_over}, 最终分数: {self.current_score}")
                        self.stop_auto_play()

                        # 游戏结束后停止WebSocket重连
                        if self.websocket_handler:
                            self.websocket_handler.should_reconnect = False

                    time.sleep(0.2)  # 增加间隔，减少CPU占用

                except KeyboardInterrupt:
                    self.logger.info("用户中断程序")
                    break
                except Exception as e:
                    # 检查是否是页面连接断开错误
                    if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                        self.logger.warning("页面连接断开，退出主循环")
                        break
                    else:
                        self.logger.error(f"主循环错误: {e}")
                        time.sleep(1)
            
        except Exception as e:
            self.logger.error(f"程序运行失败: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        try:
            self.logger.info("正在清理资源...")

            # 停止自动游戏
            self.is_auto_playing = False

            # 停止WebSocket重连
            if self.websocket_handler:
                self.websocket_handler.should_reconnect = False

            # 停止网络监听
            if self.page:
                try:
                    self.page.listen.stop()
                    self.logger.info("网络监听已停止")
                except Exception as e:
                    self.logger.debug(f"停止网络监听时出错: {e}")

            # 断开WebSocket
            if self.websocket_handler:
                try:
                    if self.loop and not self.loop.is_closed():
                        # 设置超时，避免无限等待
                        future = asyncio.run_coroutine_threadsafe(
                            self.websocket_handler.disconnect(),
                            self.loop
                        )
                        future.result(timeout=3)  # 3秒超时
                        self.logger.info("WebSocket连接已断开")
                except Exception as e:
                    self.logger.debug(f"断开WebSocket时出错: {e}")

            # 关闭事件循环
            if self.loop and not self.loop.is_closed():
                try:
                    self.loop.call_soon_threadsafe(self.loop.stop)
                except Exception as e:
                    self.logger.debug(f"停止事件循环时出错: {e}")

            # 关闭浏览器
            if self.page:
                try:
                    self.page.quit()
                    self.logger.info("浏览器已关闭")
                except Exception as e:
                    self.logger.debug(f"关闭浏览器时出错: {e}")

            self.logger.info("资源清理完成")

        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")

if __name__ == "__main__":
    player = Game2048AutoPlayer()
    player.run()
