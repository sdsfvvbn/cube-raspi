# config.py
# 硬體腳位與參數設定

# --- GPIO 腳位 (BCM 編號) ---
PIN_BASE     = 19  # 底座
PIN_SHOULDER = 13  # 肩膀 (左)
PIN_ELBOW    = 12  # 手肘 (右/Middle)
PIN_GRIPPER  = 18  # 夾爪

# --- PWM 極限範圍 (保護馬達用) ---
# 格式: [最小值, 最大值]
LIMITS = {
    'base':     [900, 2300],
    'shoulder': [1000, 1700], # 不要太後仰以免倒
    'elbow':    [1700, 2300],
    'gripper':  [1450, 2350]
}

# --- 夾爪狀態 ---
GRIPPER_OPEN  = 1450
GRIPPER_CLOSE = 2350

# --- 移動速度設定 ---
# 手臂 (求穩)
SPEED_NORMAL = 0.01
STEP_NORMAL  = 10

# 夾爪 (求快)
SPEED_FAST   = 0.005
STEP_FAST    = 50
