# 2048游戏AI算法模块
import copy
import random
import math
import time
import asyncio
from typing import List, Tuple, Optional, Dict
from config import *

class Game2048AI:
    def __init__(self):
        self.directions = DIRECTIONS
        # 位置权重矩阵 - 蛇形权重，左上角最大
        self.position_weights = [
            [32768, 16384, 8192, 4096],
            [2048,  1024,  512,  256],
            [128,   64,    32,   16],
            [8,     4,     2,    1]
        ]
        # 置换表缓存
        self.transposition_table: Dict[tuple, Tuple[int, float]] = {}
        # 迭代深化相关
        self.time_limit = 0.1  # 100ms时间限制
        self.max_search_depth = 6
        
        

    async def get_best_move(self, board: List[List[int]], current_score: int = 0) -> str:
        """获取最佳移动方向 - 仅使用本地期望最大化搜索"""
        best_score = -float('inf')
        best_move = None
        start_time = time.time()
        
        # 根据棋盘状态动态调整搜索参数
        empty_cells = len(self.get_empty_cells(board))
        max_tile = self.get_max_tile(board)
        
        # 动态调整时间限制
        if empty_cells <= 4:  # 接近终局
            self.time_limit = 0.2  # 给予更多思考时间
        elif max_tile >= 2048:  # 大数字出现
            self.time_limit = 0.15
        else:
            self.time_limit = 0.1
            
        # 动态调整最大搜索深度
        if empty_cells <= 4:
            self.max_search_depth = 8
        elif max_tile >= 2048:
            self.max_search_depth = 7
        else:
            self.max_search_depth = 6

        # 仅使用本地计算的期望最大化搜索

        # 迭代深化：从深度2开始，逐步增加
        for depth in range(2, self.max_search_depth + 1):
            if time.time() - start_time > self.time_limit:
                break

            current_best_score = -float('inf')
            current_best_move = None

            for direction in self.directions:
                new_board = self.move_board(board, direction)
                if new_board != board:
                    # 死局检测
                    if self.is_game_over(new_board):
                        continue  # 该方向会直接死，跳过
                    score = self.expectimax(new_board, depth - 1, False)
                    if score > current_best_score:
                        current_best_score = score
                        current_best_move = direction

            # 如果找到了更好的移动，更新最佳选择
            if current_best_move is not None:
                best_score = current_best_score
                best_move = current_best_move

        # 如果所有方向都会死，随机选择一个能移动的方向
        if best_move is None:
            valid_moves = [d for d in self.directions if self.move_board(board, d) != board]
            best_move = random.choice(valid_moves) if valid_moves else None

        # 清理置换表，防止内存过度使用
        if len(self.transposition_table) > 10000:
            self.transposition_table.clear()

        return best_move
    
    def expectimax(self, board: List[List[int]], depth: int, is_player_turn: bool) -> float:
        """期望最大化算法 - 带置换表缓存"""
        # 检查置换表
        board_key = tuple(tuple(row) for row in board)
        if board_key in self.transposition_table:
            cached_depth, cached_score = self.transposition_table[board_key]
            if cached_depth >= depth:
                return cached_score

        if depth == 0:
            score = self.evaluate_board(board)
            self.transposition_table[board_key] = (depth, score)
            return score

        if is_player_turn:
            # 玩家回合：选择最大值
            max_score = 0
            for direction in self.directions:
                new_board = self.move_board(board, direction)
                if new_board != board:  # 移动有效
                    score = self.expectimax(new_board, depth - 1, False)
                    max_score = max(max_score, score)

            self.transposition_table[board_key] = (depth, max_score)
            return max_score
        else:
            # 随机回合：计算期望值 - 使用概率采样优化
            empty_cells = self.get_empty_cells(board)
            if not empty_cells:
                score = self.evaluate_board(board)
                self.transposition_table[board_key] = (depth, score)
                return score

            # 概率采样：如果空格太多，只选择最靠近角落的几个
            if len(empty_cells) > 6:
                # 按到左上角的距离排序，选择前4个
                empty_cells.sort(key=lambda pos: pos[0] + pos[1])
                empty_cells = empty_cells[:4]

            expected_score = 0
            for row, col in empty_cells:
                # 90%概率出现2，10%概率出现4
                for value, prob in [(2, 0.9), (4, 0.1)]:
                    new_board = copy.deepcopy(board)
                    new_board[row][col] = value
                    score = self.expectimax(new_board, depth - 1, True)
                    expected_score += prob * score / len(empty_cells)

            self.transposition_table[board_key] = (depth, expected_score)
            return expected_score
    
    def evaluate_board(self, board: List[List[int]]) -> float:
        """评估棋盘状态 - 优化版本"""
        empty_cells = len(self.get_empty_cells(board))
        smoothness = self.calculate_smoothness(board)
        monotonicity = self.calculate_monotonicity(board)
        max_tile = self.get_max_tile(board)
        positional_score = self.calculate_positional_score(board)
        merge_potential = self.calculate_merge_potential(board)
        island_penalty = self.calculate_island_penalty(board)
        max_tile_distance = self.calculate_max_tile_distance(board)
        
        # 最大块在角落的奖励
        corner_bonus = 0
        if self.is_max_tile_in_corner(board):
            corner_bonus = max_tile * 2  # 给予显著奖励
        
        # 惩罚被困大数
        trapped_penalty = self.calculate_trapped_penalty(board)
        
        # 奖励空行/空列
        empty_line_bonus = self.calculate_empty_line_bonus(board)

        # 使用优化后的权重
        score = (
            EMPTY_WEIGHT * empty_cells +
            SMOOTHNESS_WEIGHT * smoothness +
            MONOTONICITY_WEIGHT * monotonicity +
            MAX_WEIGHT * (math.log2(max_tile) if max_tile > 0 else 0) +
            POSITION_WEIGHT * positional_score +
            MERGE_POTENTIAL_WEIGHT * merge_potential +
            corner_bonus -  # 添加角落奖励
            trapped_penalty +  # 减去被困惩罚
            empty_line_bonus -  # 添加空行/空列奖励
            ISLAND_PENALTY_WEIGHT * island_penalty -  # 孤岛惩罚
            MAX_TILE_DISTANCE_WEIGHT * max_tile_distance  # 最大块距离角落
        )

        return score

    def calculate_positional_score(self, board: List[List[int]]) -> float:
        """计算位置权重分数"""
        score = 0
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] > 0:
                    score += board[i][j] * self.position_weights[i][j]
        return score

    def calculate_merge_potential(self, board: List[List[int]]) -> float:
        """计算合并潜力 - 统计相邻且相同的块对数"""
        potential = 0
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] != 0:
                    # 检查右边
                    if j < BOARD_SIZE - 1 and board[i][j] == board[i][j + 1]:
                        potential += 1
                    # 检查下边
                    if i < BOARD_SIZE - 1 and board[i][j] == board[i + 1][j]:
                        potential += 1
        return potential
    
    def calculate_smoothness(self, board: List[List[int]]) -> float:
        """计算平滑度"""
        smoothness = 0
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] != 0:
                    # 检查右边
                    if j < BOARD_SIZE - 1 and board[i][j + 1] != 0:
                        smoothness -= abs(math.log2(board[i][j]) - math.log2(board[i][j + 1]))
                    # 检查下边
                    if i < BOARD_SIZE - 1 and board[i + 1][j] != 0:
                        smoothness -= abs(math.log2(board[i][j]) - math.log2(board[i + 1][j]))
        return smoothness
    
    def calculate_monotonicity(self, board: List[List[int]]) -> float:
        """计算单调性 - 严格遵循左上角策略"""
        # 只计算从左到右递减和从上到下递减的单调性
        row_monotonicity = 0
        col_monotonicity = 0

        # 检查行的单调性（从左到右递减）
        for i in range(BOARD_SIZE):
            current = 0
            while current < BOARD_SIZE and board[i][current] == 0:
                current += 1

            if current >= BOARD_SIZE:
                continue

            next_pos = current + 1
            while next_pos < BOARD_SIZE:
                while next_pos < BOARD_SIZE and board[i][next_pos] == 0:
                    next_pos += 1

                if next_pos >= BOARD_SIZE:
                    break

                current_value = math.log2(board[i][current])
                next_value = math.log2(board[i][next_pos])

                if current_value < next_value:  # 惩罚递增的情况
                    row_monotonicity += (next_value - current_value) * 2
                else:  # 奖励递减的情况
                    row_monotonicity += (current_value - next_value)

                current = next_pos
                next_pos += 1

        # 检查列的单调性（从上到下递减）
        for j in range(BOARD_SIZE):
            current = 0
            while current < BOARD_SIZE and board[current][j] == 0:
                current += 1

            if current >= BOARD_SIZE:
                continue

            next_pos = current + 1
            while next_pos < BOARD_SIZE:
                while next_pos < BOARD_SIZE and board[next_pos][j] == 0:
                    next_pos += 1

                if next_pos >= BOARD_SIZE:
                    break

                current_value = math.log2(board[current][j])
                next_value = math.log2(board[next_pos][j])

                if current_value < next_value:  # 惩罚递增的情况
                    col_monotonicity += (next_value - current_value) * 2
                else:  # 奖励递减的情况
                    col_monotonicity += (current_value - next_value)

                current = next_pos
                next_pos += 1

        return row_monotonicity + col_monotonicity
    
    def get_max_tile(self, board: List[List[int]]) -> int:
        """获取最大数字"""
        max_tile = 0
        for row in board:
            for cell in row:
                max_tile = max(max_tile, cell)
        return max_tile
    
    def get_empty_cells(self, board: List[List[int]]) -> List[Tuple[int, int]]:
        """获取空白格子位置"""
        empty_cells = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] == 0:
                    empty_cells.append((i, j))
        return empty_cells
    
    def move_board(self, board: List[List[int]], direction: str) -> List[List[int]]:
        """模拟移动棋盘"""
        new_board = copy.deepcopy(board)
        
        if direction == "left":
            new_board = self.move_left(new_board)
        elif direction == "right":
            new_board = self.move_right(new_board)
        elif direction == "up":
            new_board = self.move_up(new_board)
        elif direction == "down":
            new_board = self.move_down(new_board)
        
        return new_board
    
    def move_left(self, board: List[List[int]]) -> List[List[int]]:
        """向左移动"""
        for i in range(BOARD_SIZE):
            board[i] = self.merge_line(board[i])
        return board
    
    def move_right(self, board: List[List[int]]) -> List[List[int]]:
        """向右移动"""
        for i in range(BOARD_SIZE):
            board[i] = self.merge_line(board[i][::-1])[::-1]
        return board
    
    def move_up(self, board: List[List[int]]) -> List[List[int]]:
        """向上移动"""
        for j in range(BOARD_SIZE):
            column = [board[i][j] for i in range(BOARD_SIZE)]
            merged_column = self.merge_line(column)
            for i in range(BOARD_SIZE):
                board[i][j] = merged_column[i]
        return board
    
    def move_down(self, board: List[List[int]]) -> List[List[int]]:
        """向下移动"""
        for j in range(BOARD_SIZE):
            column = [board[i][j] for i in range(BOARD_SIZE)]
            merged_column = self.merge_line(column[::-1])[::-1]
            for i in range(BOARD_SIZE):
                board[i][j] = merged_column[i]
        return board
    
    def merge_line(self, line: List[int]) -> List[int]:
        """合并一行"""
        # 移除零
        non_zero = [x for x in line if x != 0]
        
        # 合并相同数字
        merged = []
        i = 0
        while i < len(non_zero):
            if i < len(non_zero) - 1 and non_zero[i] == non_zero[i + 1]:
                merged.append(non_zero[i] * 2)
                i += 2
            else:
                merged.append(non_zero[i])
                i += 1
        
        # 补零
        while len(merged) < BOARD_SIZE:
            merged.append(0)
        
        return merged
    
    def is_max_tile_in_corner(self, board: List[List[int]]) -> bool:
        max_tile = self.get_max_tile(board)
        corners = [board[0][0], board[0][-1], board[-1][0], board[-1][-1]]
        return max_tile in corners

    def is_game_over(self, board: List[List[int]]) -> bool:
        if self.get_empty_cells(board):
            return False
        for direction in self.directions:
            if self.move_board(board, direction) != board:
                return False
        return True

    def calculate_trapped_penalty(self, board: List[List[int]]) -> float:
        """计算被困大数的惩罚"""
        penalty = 0
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] >= 128:  # 只考虑较大的数字
                    # 检查周围是否有相同数字或空格
                    has_same_or_empty = False
                    for di, dj in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        ni, nj = i + di, j + dj
                        if (0 <= ni < BOARD_SIZE and 0 <= nj < BOARD_SIZE and
                            (board[ni][nj] == 0 or board[ni][nj] == board[i][j])):
                            has_same_or_empty = True
                            break
                    if not has_same_or_empty:
                        penalty += board[i][j]  # 惩罚与被困数字大小成正比
        return penalty

    def calculate_empty_line_bonus(self, board: List[List[int]]) -> float:
        """计算空行/空列的奖励"""
        bonus = 0
        # 检查空行
        for i in range(BOARD_SIZE):
            if all(cell == 0 for cell in board[i]):
                bonus += 1000  # 空行奖励
        # 检查空列
        for j in range(BOARD_SIZE):
            if all(board[i][j] == 0 for i in range(BOARD_SIZE)):
                bonus += 1000  # 空列奖励
        return bonus

    def calculate_island_penalty(self, board: List[List[int]]) -> int:
        """计算棋盘中孤立块的数量"""
        visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        islands = 0

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] != 0 and not visited[i][j]:
                    islands += 1
                    stack = [(i, j)]
                    visited[i][j] = True
                    while stack:
                        x, y = stack.pop()
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nx, ny = x + dx, y + dy
                            if (
                                0 <= nx < BOARD_SIZE
                                and 0 <= ny < BOARD_SIZE
                                and board[nx][ny] != 0
                                and not visited[nx][ny]
                            ):
                                visited[nx][ny] = True
                                stack.append((nx, ny))

        return islands

    def calculate_max_tile_distance(self, board: List[List[int]]) -> int:
        """计算最大块距离四个角的最小曼哈顿距离"""
        max_tile = self.get_max_tile(board)
        positions = [
            (i, j)
            for i in range(BOARD_SIZE)
            for j in range(BOARD_SIZE)
            if board[i][j] == max_tile
        ]
        if not positions:
            return 0

        corners = [(0, 0), (0, BOARD_SIZE - 1), (BOARD_SIZE - 1, 0), (BOARD_SIZE - 1, BOARD_SIZE - 1)]
        min_distance = BOARD_SIZE * 2
        for pos in positions:
            for corner in corners:
                distance = abs(pos[0] - corner[0]) + abs(pos[1] - corner[1])
                if distance < min_distance:
                    min_distance = distance

        return min_distance
