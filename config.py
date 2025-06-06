# 2048游戏自动化配置文件

# WebSocket配置
WEBSOCKET_BASE_URL = "wss://2048.linux.do/ws?token="
# Token将从页面动态获取

# 游戏网页URL
GAME_URL = "https://2048.linux.do/"

# 游戏参数
BOARD_SIZE = 4
DIRECTIONS = ["up", "down", "left", "right"]

# AI算法参数
MAX_DEPTH = 4  # 搜索深度（迭代深化会动态调整）
# 优化后的权重系数
SMOOTHNESS_WEIGHT = 0.1
MONOTONICITY_WEIGHT = 1.0
EMPTY_WEIGHT = 2.7
MAX_WEIGHT = 1.0
POSITION_WEIGHT = 1.0  # 位置权重
MERGE_POTENTIAL_WEIGHT = 0.5  # 合并潜力权重
ISLAND_PENALTY_WEIGHT = 1.0  # 孤岛惩罚权重
MAX_TILE_DISTANCE_WEIGHT = 1.0  # 最大块距离角落的惩罚权重
# 行合并缓存大小
LINE_CACHE_SIZE = 65536
# 边缘权重，用于鼓励在边缘保留较大数字
EDGE_WEIGHT = 0.1

# 是否启用GPU/Numba加速
USE_GPU_ACCELERATION = False

# 延迟设置（秒）
MOVE_DELAY = 0.5  # 每次移动之间的延迟
RECONNECT_DELAY = 5  # WebSocket重连延迟

# 浏览器设置
BROWSER_HEADLESS = False  # 是否无头模式
BROWSER_TIMEOUT = 30  # 页面加载超时时间
