# config.py
# 這裡存放所有「寫死」的座標數值 (PWM Pulse Width)
# 數值範圍通常在 500 (0度) ~ 2500 (180度) 之間

# GPIO 腳位設定 (對照你的 README)
PIN_BASE = 19      # 底座
PIN_SHOULDER = 13  # 肩膀 (前後)
PIN_ELBOW = 12     # 手肘 (上下)
PIN_GRIPPER = 18   # 夾爪

# 夾爪狀態
GRIPPER_OPEN = 900   # 鬆開數值 (請自行微調)
GRIPPER_CLOSE = 1860  # 夾緊數值 (請自行微調)

# === 預設位置 (Home) ===
HOME_POS = {
    'base': 1420,     # 中間
    'shoulder': 1500, # 垂直
    'elbow': 1700     # 垂直
}

# === 動作 1: 抓取點 (Pickup Point) - 供料區位置 ===
PICKUP_HOVER = {'base': 1780, 'shoulder': 1500, 'elbow': 2000} # 準備抓取(高處)
PICKUP_DOWN  = {'base': 1780, 'shoulder': 1000, 'elbow': 2000} # 下去抓(低處)

# === 動作 2: 放置點 (Place Point) - 堆疊位置 ===
PLACE_HOVER  = {'base': 1420, 'shoulder': 1500, 'elbow': 2300} # 準備放置(高處)
PLACE_DOWN   = {'base': 1420, 'shoulder': 1250, 'elbow': 2300} # 下去放(低處)


# config.py 的最下面

# === 金字塔模式 (2cm 小積木專用版) ===
# 策略：微小間隙 (Small Gap) + 高度墊高 (Stacking)
# 中間值 Base: 1420
# config.py 的最下面

# === 金字塔模式 (前後排列版 - 直線型) ===
# 策略：利用夾爪左右張開的特性，前後放置避免干涉
# Base 全部固定在 1420 (中間)，只改變 Elbow (遠近)

PYRAMID_POSITIONS = [
    # [第 1 顆] 放最遠 (Far)
    # 使用你的極限伸展 2300
    {
        'name': 'Bottom_Far', # 遠
        'hover': {'base': 1420, 'shoulder': 1500, 'elbow': 2300},
        'down':  {'base': 1420, 'shoulder': 1250, 'elbow': 2300} 
    },
    
    # [第 2 顆] 放最近 (Near)
    # Elbow 收回來一點 (例如 1900)，要留出 2cm 以上的空間
    {
        'name': 'Bottom_Near', # 近
        'hover': {'base': 1420, 'shoulder': 1500, 'elbow': 1900},
        'down':  {'base': 1420, 'shoulder': 1250, 'elbow': 1900}
    },

    # [第 3 顆] 放中間 (Top)
    # Elbow 在兩者中間 (例如 2100)
    # Shoulder 抬高 (1280)
    {
        'name': 'Top_Center',
        'hover': {'base': 1420, 'shoulder': 1500, 'elbow': 2100},
        'down':  {'base': 1420, 'shoulder': 1300, 'elbow': 2100} 
    }
]
