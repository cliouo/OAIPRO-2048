import os
import asyncio
import aiohttp
import json
import time
from typing import List, Optional

class OpenAIHelper:
    def __init__(self):
        # self.api_key = os.environ.get("OPENAI_API_KEY")
        self.api_key = "sk-xxxx"
        # 使用多个备用API地址
        self.api_bases = [
            "https://oaipro.com/v1"
        ]
        self.current_api_index = 0
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # API调用控制
        self.last_call_time = 0
        self.min_call_interval = 3  # 最小调用间隔（秒）
        self.max_calls_per_minute = 10  # 每分钟最大调用次数
        self.call_times = []  # 记录调用时间

    def _can_make_request(self) -> bool:
        """检查是否可以发起新的请求"""
        current_time = time.time()
        
        # 检查最小调用间隔
        if current_time - self.last_call_time < self.min_call_interval:
            return False
            
        # 清理超过1分钟的记录
        self.call_times = [t for t in self.call_times if current_time - t < 60]
        
        # 检查每分钟调用次数
        if len(self.call_times) >= self.max_calls_per_minute:
            return False
            
        return True

    def _update_call_stats(self):
        """更新调用统计"""
        current_time = time.time()
        self.last_call_time = current_time
        self.call_times.append(current_time)

    async def get_move_suggestion(self, board: List[List[int]]) -> Optional[str]:
        """获取AI建议的移动方向"""
        # 检查是否可以发起请求
        if not self._can_make_request():
            print("⚠️ API调用过于频繁，等待冷却...")
            return None
            
        try:
            api_base = self.api_bases[self.current_api_index]
            async with aiohttp.ClientSession() as session:
                prompt = self._create_prompt(board)
                data = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "你是一个2048游戏专家，请根据当前棋盘状态给出最佳移动方向。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 50
                }
                
                async with session.post(
                    f"{api_base}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        move = result["choices"][0]["message"]["content"].strip().upper()
                        if move in ["UP", "DOWN", "LEFT", "RIGHT"]:
                            self._update_call_stats()  # 更新调用统计
                            return move
                    else:
                        print(f"API调用失败: {response.status}")
                        
        except Exception as e:
            print(f"获取AI建议失败: {e}")
            
        return None

    def _create_prompt(self, board: List[List[int]]) -> str:
        """创建提示词"""
        board_str = "\n".join([" ".join(map(str, row)) for row in board])
        return f"""当前2048游戏棋盘状态如下：

{board_str}

请分析当前局势，并给出最佳移动方向（UP/DOWN/LEFT/RIGHT）。
只需要回答方向，不需要解释。"""

    def should_consult_ai(self, board: List[List[int]]) -> bool:
        """判断是否应该咨询AI"""
        # 检查是否可以发起请求
        if not self._can_make_request():
            return False
            
        empty_cells = sum(1 for row in board for cell in row if cell == 0)
        max_tile = max(max(row) for row in board)
        
        # 当空格较少或出现大数字时咨询AI
        return empty_cells <= 4 or max_tile >= 2048

    async def get_ai_move(self, board: List[List[int]]) -> Optional[str]:
        """获取AI移动建议"""
        if self.should_consult_ai(board):
            return await self.get_move_suggestion(board)
        return None

async def main():
    # 测试代码
    helper = OpenAIHelper()
    test_board = [
        [2, 4, 8, 16],
        [4, 8, 16, 32],
        [8, 16, 32, 64],
        [16, 32, 64, 128]
    ]
    move = await helper.get_ai_move(test_board)
    print(f"AI建议移动: {move}")

if __name__ == "__main__":
    asyncio.run(main()) 