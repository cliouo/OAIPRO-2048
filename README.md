# 2048游戏自动化脚本

这是一个使用Python开发的2048游戏自动化脚本，可以自动玩 https://2048.linux.do/ 网站上的2048游戏。

## 功能特点

- 🤖 智能AI算法：使用期望最大化算法进行决策
- 🌐 WebSocket实时通信：监听游戏状态并发送移动指令
- 🎮 网页自动化：使用DrissionPage控制浏览器
- 🔧 动态Token获取：自动从页面提取WebSocket token
- 📊 实时状态显示：显示当前分数和连接状态
- 🎯 用户友好界面：注入控制按钮到游戏页面

## 安装依赖

1. **创建并激活虚拟环境**
   ```bash
   python3 -m venv venv
   # Linux/macOS
   source venv/bin/activate
   # Windows
   # venv\Scripts\activate
   ```

2. **安装项目依赖**
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. **激活虚拟环境并运行脚本**
   ```bash
   # 确保已在项目根目录并激活 venv
   source venv/bin/activate  # Windows 使用 venv\Scripts\activate

   python 2048_auto_player.py
   ```

2. **等待页面加载**
   - 脚本会自动打开浏览器并加载游戏页面
   - 在页面右上角会出现控制面板

3. **设置WebSocket Token（如果需要）**
   - 脚本会尝试自动获取token
   - 如果自动获取失败，点击"设置Token"按钮手动输入
   - Token格式类似：`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

4. **开始自动游戏**
   - 点击"开始自动游戏"按钮
   - AI会自动分析棋盘并执行最佳移动
   - 可以随时点击"停止自动游戏"暂停

## 控制面板说明

- **开始自动游戏**：启动AI自动玩游戏
- **停止自动游戏**：暂停AI操作
- **设置Token**：手动设置WebSocket连接token
- **状态显示**：
  - 状态：当前运行状态
  - 分数：实时游戏分数
  - WebSocket：连接状态

## AI算法说明

脚本使用期望最大化（Expectimax）算法，结合以下启发式评估：

1. **空格权重**：优先保持更多空格
2. **平滑度**：相邻格子数值差异最小化
3. **单调性**：保持数值的单调递增/递减排列
4. **最大值权重**：优先产生更大的数字
5. **孤岛惩罚**：减少分散的单个方块

## 技术架构

- **主控制器**：`2048_auto_player.py` - 协调各个模块
- **AI算法**：`game_ai.py` - 实现游戏决策逻辑
- **WebSocket处理**：`websocket_handler.py` - 处理实时通信
- **配置文件**：`config.py` - 存储各种参数设置

## 故障排除

### WebSocket连接失败
1. 检查网络连接
2. 确认token是否正确
3. 尝试手动设置新的token

### 页面加载失败
1. 检查网址是否可访问
2. 确认浏览器是否正常启动
3. 尝试关闭其他浏览器实例

### AI不移动
1. 确认WebSocket连接状态
2. 检查游戏是否已结束
3. 尝试重新开始游戏

## 注意事项

- 确保网络连接稳定
- 不要在脚本运行时手动操作游戏
- Token有时效性，过期后需要重新设置
- 建议在稳定的网络环境下使用

## 许可证

本项目仅供学习和研究使用，请遵守相关网站的使用条款。
