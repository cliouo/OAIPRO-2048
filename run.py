#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2048游戏自动化脚本启动器
"""

import sys
import os

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import DrissionPage
        import websockets
        print("✓ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("🎮 2048游戏自动化脚本")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 导入并运行主程序
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("auto_player", "2048_auto_player.py")
        auto_player_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auto_player_module)
        Game2048AutoPlayer = auto_player_module.Game2048AutoPlayer
        
        print("\n🚀 启动自动化脚本...")
        player = Game2048AutoPlayer()
        player.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
