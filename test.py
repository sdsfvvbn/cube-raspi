import curses
import pigpio
import time
import config  # 匯入你的設定檔以讀取腳位

# 初始化 pigpio
pi = pigpio.pi()
if not pi.connected:
    print("❌ 無法連接 pigpio daemon，請先執行 'sudo pigpiod'")
    exit()

# 設定馬達腳位
MOTORS = {
    'Base (底座)': config.PIN_BASE,
    'Shoulder (肩膀)': config.PIN_SHOULDER,
    'Elbow (手肘)': config.PIN_ELBOW,
    'Gripper (夾爪)': config.PIN_GRIPPER
}

# 初始位置與步進值
current_pos = {
    'Base (底座)': 1500,
    'Shoulder (肩膀)': 1500,
    'Elbow (手肘)': 1800,
    'Gripper (夾爪)': config.GRIPPER_OPEN
}

step = 20  # 每次按鍵增加/減少的數值 (預設微調)

def update_servos():
    """將目前的數值寫入馬達"""
    for name, pin in MOTORS.items():
        # 安全限制：防止數值超出 SG90 極限 (500~2500)
        # MeArm 硬體結構極限可能更窄，操作時請小心
        if current_pos[name] < 500: current_pos[name] = 500
        if current_pos[name] > 2500: current_pos[name] = 2500
        
        pi.set_servo_pulsewidth(pin, current_pos[name])

def main(stdscr):
    global step
    
    # 畫面設定
    curses.curs_set(0) # 隱藏游標
    stdscr.nodelay(1)  # 非阻塞輸入
    stdscr.timeout(100) # 每 100ms 刷新一次

    # 先歸位
    update_servos()

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "=== MeArm 機械手臂校正工具 ===", curses.A_BOLD)
        stdscr.addstr(2, 0, "[操作說明]")
        stdscr.addstr(3, 2, "⬅️ ➡️ (左右鍵) : 控制 底座 (Base)")
        stdscr.addstr(4, 2, "⬆️ ⬇️ (上下鍵) : 控制 肩膀 (Shoulder)")
        stdscr.addstr(5, 2, "W / S 鍵       : 控制 手肘 (Elbow)")
        stdscr.addstr(6, 2, "O / P 鍵       : 夾爪 開/合 (Gripper)")
        stdscr.addstr(7, 2, "1 / 2 / 3 鍵   : 切換移動速度 (目前: {})".format(step))
        stdscr.addstr(8, 2, "Q 鍵           : 離開並關閉馬達")

        # 顯示目前數值 (這就是你要抄下來的數字！)
        stdscr.addstr(10, 0, "=== 目前 PWM 數值 (請記錄) ===", curses.A_REVERSE)
        row = 12
        for name, val in current_pos.items():
            stdscr.addstr(row, 2, f"{name}: {val}")
            row += 1

        key = stdscr.getch()

        if key == ord('q'):
            break
        
        # 速度切換
        elif key == ord('1'): step = 5   # 精細
        elif key == ord('2'): step = 20  # 正常
        elif key == ord('3'): step = 50  # 快速

        # 底座 (Base)
        elif key == curses.KEY_LEFT:  current_pos['Base (底座)'] += step
        elif key == curses.KEY_RIGHT: current_pos['Base (底座)'] -= step
        
        # 肩膀 (Shoulder)
        elif key == curses.KEY_UP:    current_pos['Shoulder (肩膀)'] -= step
        elif key == curses.KEY_DOWN:  current_pos['Shoulder (肩膀)'] += step
        
        # 手肘 (Elbow)
        elif key == ord('w'): current_pos['Elbow (手肘)'] -= step
        elif key == ord('s'): current_pos['Elbow (手肘)'] += step

        # 夾爪 (Gripper)
        elif key == ord('o'): current_pos['Gripper (夾爪)'] -= step
        elif key == ord('p'): current_pos['Gripper (夾爪)'] += step

        update_servos()

    # 離開前放鬆馬達
    for pin in MOTORS.values():
        pi.set_servo_pulsewidth(pin, 0)

# 執行程式
try:
    curses.wrapper(main)
except KeyboardInterrupt:
    pi.stop()
