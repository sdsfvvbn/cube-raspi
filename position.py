import sys
import select
import tty
import termios
import pigpio
import time

# ==========================================
# 1. 硬體參數 (使用您的黃金四角)
# ==========================================
PIN_GRIPPER  = 18
PIN_ELBOW    = 12
PIN_BASE     = 19
PIN_SHOULDER = 13

# 夾爪設定
GRIPPER_OPEN  = 1600
GRIPPER_CLOSE = 2350

# 初始位置 (開機時預設的位置)
current_pos = {
    'base': 1500,
    'shoulder': 1500,
    'elbow': 1550,
    'gripper': 1600
}

# 腳位對照表
PINS = {
    'base': PIN_BASE,
    'shoulder': PIN_SHOULDER,
    'elbow': PIN_ELBOW,
    'gripper': PIN_GRIPPER
}

# 移動步距 (按一下動多少)
STEP = 20

# ==========================================
# 2. 系統連線與軟啟動
# ==========================================
pi = pigpio.pi()
if not pi.connected:
    print("❌ 錯誤：pigpiod 沒開！(sudo systemctl start pigpiod)")
    exit()

def set_servo(pin, val):
    pi.set_servo_pulsewidth(pin, val)

print("🚀 系統啟動中... (執行軟啟動以保護電池)")

# 依序啟動馬達，避免電流瞬間過載
startup_sequence = ['base', 'shoulder', 'elbow', 'gripper']

for name in startup_sequence:
    pin = PINS[name]
    val = current_pos[name]
    print(f"   -> 啟動 {name}...")
    set_servo(pin, val)
    time.sleep(0.5) # 關鍵：每顆馬達間隔 0.5 秒

print("✅ 啟動完成，系統穩定！")

# ==========================================
# 3. 按鍵讀取
# ==========================================
def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return key

# ==========================================
# 4. 主程式
# ==========================================
print("\n" * 50)
print("==============================================")
print("      🎯 位置尋找器 v2 (防抖動版)")
print("==============================================")
print("【肩 Shoulder】 [A] +20 (上/後)   [Z] -20 (下/前)")
print("【肘 Elbow】    [S] +20 (前/下)   [X] -20 (後/中)")
print("【底 Base】     [D] +20 (左)      [C] -20 (右)")
print("【夾 Gripper】  [1] 開            [2] 關")
print("----------------------------------------------")
print(" [P] 印出數據 (Print Config)")
print(" [L] 離開 (Leave)")
print("==============================================")

try:
    while True:
        key = get_key().lower()
        
        # 如果沒按鍵，就稍微休息，避免佔用 CPU 和過度發送訊號
        if key == '': 
            time.sleep(0.05)
            continue

        # --- Shoulder ---
        if key == 'a': current_pos['shoulder'] += STEP
        elif key == 'z': current_pos['shoulder'] -= STEP
            
        # --- Elbow ---
        elif key == 's': current_pos['elbow'] += STEP
        elif key == 'x': current_pos['elbow'] -= STEP

        # --- Base ---
        elif key == 'd': current_pos['base'] += STEP
        elif key == 'c': current_pos['base'] -= STEP

        # --- Gripper ---
        elif key == '1': 
            current_pos['gripper'] = GRIPPER_OPEN
            print("\n🖐 夾爪: 開")
        elif key == '2': 
            current_pos['gripper'] = GRIPPER_CLOSE
            print("\n✊ 夾爪: 關")

        # --- 功能鍵 ---
        elif key == 'p':
            print(f"\n📝 記錄點: {current_pos}")
            continue # 跳過移動指令

        elif key == 'l':
            break

        # --- 安全限制 (防止撞壞) ---
        # 這裡的範圍設得比較寬，讓你可以測試極限
        # 但請隨時準備拔電源！
        for name in ['shoulder', 'elbow', 'base']:
            if current_pos[name] > 2450: current_pos[name] = 2450
            if current_pos[name] < 550: current_pos[name] = 550

        # --- 執行移動 ---
        set_servo(PIN_SHOULDER, current_pos['shoulder'])
        set_servo(PIN_ELBOW,    current_pos['elbow'])
        set_servo(PIN_BASE,     current_pos['base'])
        set_servo(PIN_GRIPPER,  current_pos['gripper'])
        
        # 即時顯示
        print(f"\r S:{current_pos['shoulder']}  E:{current_pos['elbow']}  B:{current_pos['base']}   ", end="")
        
        # 【關鍵防抖】強制休息 0.1 秒
        # 這能確保馬達有時間反應，不會因指令堆積而發抖
        time.sleep(0.1)

except KeyboardInterrupt:
    pass
finally:
    print("\n程式結束。")
    # 這裡可以選擇是否要放鬆
    # 如果怕手臂砸下來，可以把下面這行註解掉
    
    # 選擇性放鬆：只放鬆底座和夾爪，手臂保持出力
    set_servo(PIN_BASE, 0)
    set_servo(PIN_GRIPPER, 0)
    # set_servo(PIN_SHOULDER, 0) # 為了安全，這兩顆不放鬆
    # set_servo(PIN_ELBOW, 0)
    
    pi.stop()