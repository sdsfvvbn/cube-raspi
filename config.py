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
GRIPPER_CLOSE = 2300  # 夾緊數值 (請自行微調)

# === 預設位置 (Home) ===
HOME_POS = {
    'base': 1500,     # 中間
    'shoulder': 2000, # 垂直
    'elbow': 1500     # 垂直
}

# === 動作 1: 抓取點 (Pickup Point) - 供料區位置 ===
PICKUP_HOVER = {'base': 1000, 'shoulder': 1500, 'elbow': 1800} # 準備抓取(高處)
PICKUP_DOWN  = {'base': 1000, 'shoulder': 2200, 'elbow': 2000} # 下去抓(低處)

# === 動作 2: 放置點 (Place Point) - 堆疊位置 ===
PLACE_HOVER  = {'base': 2000, 'shoulder': 1800, 'elbow': 1800} # 準備放置(高處)
PLACE_DOWN   = {'base': 2000, 'shoulder': 2100, 'elbow': 1900} # 下去放(低處)
