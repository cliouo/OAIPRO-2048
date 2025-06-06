# WebSocket处理模块
import asyncio
import json
import logging
import websockets
from typing import Callable, Optional, Dict, Any
from config import *

class WebSocketHandler:
    def __init__(self, on_game_state: Callable[[Dict[str, Any]], None]):
        self.websocket = None
        self.on_game_state = on_game_state
        self.is_connected = False
        self.should_reconnect = True
        self.websocket_url = None  # 动态设置的WebSocket URL
        self.page = None  # 添加页面引用

        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def set_websocket_url(self, token: str):
        """设置WebSocket URL"""
        self.websocket_url = f"{WEBSOCKET_BASE_URL}{token}"
        self.logger.info(f"WebSocket URL已设置: {self.websocket_url}")
    
    async def connect(self):
        """连接WebSocket"""
        if not self.websocket_url:
            self.logger.error("WebSocket URL未设置，无法连接")
            return

        try:
            self.logger.info(f"正在连接WebSocket: {self.websocket_url}")
            
            # 注入WebSocket连接代码
            js_code = """
            // 创建WebSocket连接
            const ws = new WebSocket(arguments[0]);
            
            // 连接建立时的处理
            ws.onopen = function() {
                console.log('WebSocket连接已建立');
                window.gameSocket = ws;
            };
            
            // 接收消息的处理
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'game_state') {
                        window.gameState = data.data;
                    }
                } catch (e) {
                    console.error('解析WebSocket消息失败:', e);
                }
            };
            
            // 连接关闭时的处理
            ws.onclose = function() {
                console.log('WebSocket连接已关闭');
                window.gameSocket = null;
            };
            
            // 错误处理
            ws.onerror = function(error) {
                console.error('WebSocket错误:', error);
                window.gameSocket = null;
            };
            """
            
            # 执行JavaScript代码
            self.page.run_js(js_code, self.websocket_url)
            
            # 等待连接建立
            await asyncio.sleep(1)
            
            # 检查连接状态
            is_connected = self.page.run_js("return window.gameSocket && window.gameSocket.readyState === WebSocket.OPEN;")
            
            if is_connected:
                self.is_connected = True
                self.logger.info("WebSocket连接成功")
            else:
                self.logger.error("WebSocket连接失败")
                self.is_connected = False
                
            # 开始监听消息
            await self.listen_messages()
            
        except Exception as e:
            self.logger.error(f"WebSocket连接失败: {e}")
            self.is_connected = False
            if self.should_reconnect:
                self.logger.info(f"{RECONNECT_DELAY}秒后重新连接...")
                await asyncio.sleep(RECONNECT_DELAY)
                await self.connect()
    
    async def listen_messages(self):
        """监听WebSocket消息"""
        try:
            while self.is_connected and self.should_reconnect:
                try:
                    # 检查页面是否还存在
                    if not self.page:
                        self.logger.warning("页面对象不存在，停止监听")
                        self.is_connected = False
                        break

                    # 检查连接状态，添加异常处理
                    try:
                        is_connected = self.page.run_js("return window.gameSocket && window.gameSocket.readyState === WebSocket.OPEN;")
                    except Exception as page_error:
                        self.logger.warning(f"页面连接已断开: {page_error}")
                        self.is_connected = False
                        break

                    if not is_connected:
                        self.logger.warning("WebSocket连接已断开")
                        self.is_connected = False
                        break

                    # 获取游戏状态，添加异常处理
                    try:
                        game_state = self.page.run_js("return window.gameState;")
                        if game_state:
                            await self.handle_message({"type": "game_state", "data": game_state})
                    except Exception as state_error:
                        self.logger.warning(f"获取游戏状态失败: {state_error}")
                        # 不立即断开连接，可能只是临时问题

                    # 等待一段时间
                    await asyncio.sleep(0.2)  # 增加间隔，减少CPU占用

                except Exception as e:
                    self.logger.error(f"处理消息错误: {e}")
                    # 如果是连接相关错误，停止重连
                    if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                        self.should_reconnect = False
                        self.is_connected = False
                        break

        except Exception as e:
            self.logger.error(f"监听消息错误: {e}")
            self.is_connected = False
            # 只有在明确需要重连且页面仍然存在时才重连
            if self.should_reconnect and self.page:
                self.logger.info(f"{RECONNECT_DELAY}秒后尝试重连...")
                await asyncio.sleep(RECONNECT_DELAY)
                await self.connect()
    
    async def handle_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        message_type = data.get("type")
        
        if message_type == "game_state":
            game_data = data.get("data", {})
            self.logger.info(f"收到游戏状态: 分数={game_data.get('score', 0)}")

            # 调用回调函数处理游戏状态
            if self.on_game_state:
                self.on_game_state(game_data)

        elif message_type == "error":
            self.logger.error(f"服务器错误: {data.get('message', '未知错误')}")
            if self.on_game_state:
                # 通知上层移动无效，以便继续下一步
                self.on_game_state(None)
            
        else:
            self.logger.info(f"收到未知消息类型: {message_type}")
    
    async def send_move(self, direction: str):
        """发送移动指令"""
        if not self.is_connected:
            self.logger.warning("WebSocket未连接，无法发送移动指令")
            return False
        
        try:
            message = {
                "type": "move",
                "data": {
                    "direction": direction
                }
            }
            
            # 通过页面JavaScript发送消息
            js_code = f"""
            if (window.gameSocket && window.gameSocket.readyState === WebSocket.OPEN) {{
                window.gameSocket.send(JSON.stringify({message}));
                return true;
            }}
            return false;
            """
            
            result = self.page.run_js(js_code)
            if result:
                self.logger.info(f"发送移动指令: {direction}")
                return True
            else:
                self.logger.warning("无法发送移动指令：WebSocket未连接")
                return False
            
        except Exception as e:
            self.logger.error(f"发送移动指令失败: {e}")
            self.is_connected = False
            return False
    
    async def send_message(self, message: Dict[str, Any]):
        """发送自定义消息"""
        if not self.is_connected:
            self.logger.warning("WebSocket未连接，无法发送消息")
            return False
        
        try:
            # 通过页面JavaScript发送消息
            js_code = f"""
            if (window.gameSocket && window.gameSocket.readyState === WebSocket.OPEN) {{
                window.gameSocket.send(JSON.stringify({message}));
                return true;
            }}
            return false;
            """
            
            result = self.page.run_js(js_code)
            if result:
                self.logger.info(f"发送消息: {message}")
                return True
            else:
                self.logger.warning("无法发送消息：WebSocket未连接")
                return False
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        self.should_reconnect = False
        self.is_connected = False

        # 关闭WebSocket连接
        if self.page:
            try:
                js_code = """
                if (window.gameSocket) {
                    window.gameSocket.close();
                    window.gameSocket = null;
                }
                """
                self.page.run_js(js_code)
                self.logger.info("WebSocket连接已断开")
            except Exception as e:
                self.logger.debug(f"断开WebSocket时出错: {e}")
        else:
            self.logger.info("页面不存在，WebSocket连接已标记为断开")
    
    def get_connection_status(self) -> bool:
        """获取连接状态"""
        if not self.page or not self.is_connected:
            return False

        try:
            return self.page.run_js("return window.gameSocket && window.gameSocket.readyState === WebSocket.OPEN;")
        except Exception as e:
            # 页面连接断开时，标记为不需要重连
            self.logger.debug(f"检查连接状态失败: {e}")
            self.is_connected = False
            if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                self.should_reconnect = False
            return False
