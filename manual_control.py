import pigpio
import time
import config

# 初始化
pi = pigpio.pi()
if not pi.connected:
    print("❌ pigpiod 未啟動 (sudo systemctl start pigpiod)")
    exit()

# 目前位置
current_pos = {
    config.PIN_BASE: 1500,
    config.PIN_SHOULDER: 1500,
    config.PIN_ELBOW: 1800, # 預設抬高一點
    config.PIN_GRIPPER: config.GRIPPER_OPEN
}

# 腳位對應
PINS = {
    'b': config.PIN_BASE,
    's': config.PIN_SHOULDER,
    'e': config.PIN_ELBOW,
    'g': config.PIN_GRIPPER
}

def move_servo(pin, target):
    """ 智慧移動：自動判斷夾爪加速 """
    start = current_pos[pin]
    
    # 判斷速度
    if pin == config.PIN_GRIPPER:
        speed = config.SPEED_FAST
        step  = config.STEP_FAST
    else:
        speed = config.SPEED_NORMAL
        step  = config.STEP_NORMAL

    if target > start: step_dir = step
    else: step_dir = -step

    # 移動迴圈
    for pwm in range(start, target, step_dir):
        pi.set_servo_pulsewidth(pin, pwm)
        time.sleep(speed)
    
    pi.set_servo_pulsewidth(pin, target)
    current_pos[pin] = target

# --- 主程式 ---
print("=== MeArm 手動控制台 ===")
print("指令格式: 代號 數值 (例如: b 1600)")
print("代號: b(底座), s(肩), e(肘), g(夾)")
print("輸入 'p' 印出目前所有座標 (方便寫腳本)")
print("輸入 'q' 離開")

try:
    # 開機歸位
    for p, v in current_pos.items():
        pi.set_servo_pulsewidth(p, v)
        time.sleep(0.5)

    while True:
        cmd = input(">> ").strip().lower()
        if cmd == 'q': break
        
        if cmd == 'p':
            print(f"\n📝 [RECORD] {list(current_pos.values())} (順序: Base, Shoulder, Elbow, Gripper)\n")
            continue

        try:
            parts = cmd.split()
            if len(parts) != 2: continue
            
            key, val = parts[0], int(parts[1])
            if key in PINS:
                move_servo(PINS[key], val)
        except ValueError:
            print("❌ 錯誤指令")

finally:
    for p in PINS.values(): pi.set_servo_pulsewidth(p, 0)
    pi.stop()
