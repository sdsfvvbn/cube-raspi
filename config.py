# config.py - 您的 MeArm 專屬設定檔

# --- 1. GPIO 腳位設定 (使用 BCM 編號) ---
PIN_GRIPPER  = 18  # 夾爪
PIN_ELBOW    = 12  # Middle (右臂/肘)
PIN_BASE     = 19  # 底座
PIN_SHOULDER = 13  # 左臂 (肩)

# --- 2. 馬達轉動極限 (PWM 脈衝寬度) ---
# 夾爪: [張開, 閉合]
LIMIT_GRIPPER = [1600, 2350]

# 底座: [最右, 最左]
LIMIT_BASE = [900, 2000]

# 左臂 (Shoulder): [最低, 最高]
LIMIT_SHOULDER = [1550, 2350]

# 右臂 (Middle/Elbow): [最低, 最高]
LIMIT_ELBOW = [1000, 1700]

# --- 3. 戰場地圖 ---
FEEDER_LOCATIONS = {
    "2x4": [0, 180, 20],
    "2x2": [-50, 160, 20],
}

BUILD_ORIGIN = [150, 0, 10]