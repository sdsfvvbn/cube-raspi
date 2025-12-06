import sys
import select
import tty
import termios
import pigpio
import time

# ==========================================
# 1. 您的專屬設定 (依照您的要求)
# ==========================================

# GPIO 腳位 (請確認是否與 config.py 一致)
PIN_GRIPPER  = 18
PIN_ELBOW    = 12
PIN_BASE     = 19
PIN_SHOULDER = 13

# 夾爪設定 (1=開, 2=關)
GRIPPER_OPEN_PWM  = 1600  # 1: 開
GRIPPER_CLOSE_PWM = 2350  # 2: 關

# 初始位置 (開機時的狀態)
current_pos = {
    'base': 1500,      # 中間
    'shoulder': 1500,  # 起點
    'elbow': 1550,     # 中間
    'gripper': GRIPPER_OPEN_PWM
}

# 微調步伐 (按一下加減多少)
STEP = 20

# ==========================================
# 2. 系統連線
# ==========================================
pi = pigpio.pi()
if not pi.connected:
    print("❌ 錯誤：pigpiod 沒開！請執行 sudo systemctl start pigpiod")
    exit()

def set_servo(pin, val):
    pi.set_servo_pulsewidth(pin, val)

# 讓所有馬達歸位
# 讓所有馬達歸位 (改良版：排隊啟動)
print("正在歸位 (一顆一顆來)...")

# 定義啟動順序 (建議：底座 -> 手臂 -> 夾爪)
# 這樣可以避免手臂還沒站穩就亂動
startup_order = ['base', 'shoulder', 'elbow', 'gripper']

for name in startup_order:
    pin = 0
    if name == 'base': pin = PIN_BASE
    elif name == 'shoulder': pin = PIN_SHOULDER
    elif name == 'elbow': pin = PIN_ELBOW
    elif name == 'gripper': pin = PIN_GRIPPER
    
    val = current_pos[name]
    
    print(f"   -> 啟動 {name}...")
    set_servo(pin, val)
    
    # 【關鍵】每啟動一顆，休息 0.5 秒，讓電壓回穩
    time.sleep(0.5) 

print("✅ 歸位完成，系統穩定！")

# ==========================================
# 3. 按鍵讀取函式 (不用按 Enter)
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
# 4. 主畫面與操作說明
# ==========================================
print("\n" * 50) # 清空畫面
print("==============================================")
print("      🎯 機械手臂 定位尋找器 (Position Finder)")
print("==============================================")
print("【肩 Shoulder】(1500~1700)")
print("   [A] +20 (往上/後)   [Z] -20 (往下/前)")
print("   [Q] 一鍵到 1700     [E] 一鍵回 1500")
print("----------------------------------------------")
print("【肘 Elbow】(1550~1900)")
print("   [S] +20 (往前/下)   [X] -20 (往後/中)")
print("   [W] 一鍵到 1900     [R] 一鍵回 1550")
print("----------------------------------------------")
print("【底 Base】")
print("   [D] +20 (左)        [C] -20 (右)")
print("   [F] 一鍵回中 (1500)")
print("----------------------------------------------")
print("【夾 Gripper】")
print("   [1] 開 (Open)       [2] 關 (Close)")
print("----------------------------------------------")
print(" [P] 顯示目前座標 (請抄下來！)")
print(" [L] 離開程式")
print("==============================================")

try:
    while True:
        key = get_key().lower()
        
        if key == '': continue

        # --- Shoulder (肩膀) 控制 ---
        if key == 'a': 
            current_pos['shoulder'] += STEP
        elif key == 'z': 
            current_pos['shoulder'] -= STEP
        elif key == 'q': # 一鍵最大
            current_pos['shoulder'] = 1700
        elif key == 'e': # 一鍵回中
            current_pos['shoulder'] = 1500
            
        # --- Elbow (手肘) 控制 ---
        elif key == 's': 
            current_pos['elbow'] += STEP
        elif key == 'x': 
            current_pos['elbow'] -= STEP
        elif key == 'w': # 一鍵最大
            current_pos['elbow'] = 1900
        elif key == 'r': # 一鍵回中
            current_pos['elbow'] = 1550

        # --- Base (底座) 控制 ---
        elif key == 'd': 
            current_pos['base'] += STEP
        elif key == 'c': 
            current_pos['base'] -= STEP
        elif key == 'f': # 一鍵回中
            current_pos['base'] = 1500

        # --- Gripper (夾爪) 控制 ---
        elif key == '1': 
            current_pos['gripper'] = GRIPPER_OPEN_PWM
            print("\n🖐 夾爪: 開")
        elif key == '2': 
            current_pos['gripper'] = GRIPPER_CLOSE_PWM
            print("\n✊ 夾爪: 關")

        # --- 顯示數據 ---
        elif key == 'p':
            print(f"\n📝 請記錄: BASE={current_pos['base']}, SHOULDER={current_pos['shoulder']}, ELBOW={current_pos['elbow']}")
            continue # 跳過移動指令，直接下一輪

        # --- 離開 ---
        elif key == 'l':
            break

        # --- 限制範圍 (安全鎖) ---
        # Shoulder: 1500 ~ 1700
        if current_pos['shoulder'] > 1700: current_pos['shoulder'] = 1700
        if current_pos['shoulder'] < 1500: current_pos['shoulder'] = 1500
        
        # Elbow: 1550 ~ 1900
        if current_pos['elbow'] > 1900: current_pos['elbow'] = 1900
        if current_pos['elbow'] < 1550: current_pos['elbow'] = 1550
        
        # Base: 900 ~ 2100 (通用範圍)
        if current_pos['base'] > 2100: current_pos['base'] = 2100
        if current_pos['base'] < 900: current_pos['base'] = 900

        # --- 執行移動 ---
        set_servo(PIN_SHOULDER, current_pos['shoulder'])
        set_servo(PIN_ELBOW,    current_pos['elbow'])
        set_servo(PIN_BASE,     current_pos['base'])
        set_servo(PIN_GRIPPER,  current_pos['gripper'])
        
        # 即時顯示數值
        print(f"\r S:{current_pos['shoulder']}  E:{current_pos['elbow']}  B:{current_pos['base']}   ", end="")
        
        time.sleep(0.05) # 稍微延遲避免太快

except KeyboardInterrupt:
    pass
finally:
    print("\n程式結束，放鬆馬達...")
    set_servo(PIN_SHOULDER, 0)
    set_servo(PIN_ELBOW, 0)
    set_servo(PIN_BASE, 0)
    set_servo(PIN_GRIPPER, 0)
    pi.stop()