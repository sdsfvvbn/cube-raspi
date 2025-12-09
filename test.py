import curses
import pigpio
import time
import config

# 初始化 pigpio
pi = pigpio.pi()
if not pi.connected:
    print("❌ 無法連接 pigpio，請執行 'sudo pigpiod'")
    exit()

# 設定馬達
MOTORS = {
    'Base': config.PIN_BASE,
    'Shoulder': config.PIN_SHOULDER,
    'Elbow': config.PIN_ELBOW,
    'Gripper': config.PIN_GRIPPER
}

# 初始位置
current_pos = {
    'Base': 1500,
    'Shoulder': 1500,
    'Elbow': 1500,
    'Gripper': config.GRIPPER_OPEN
}

# 調整步進值 (加大預設值以解決力度不足問題)
STEP_FINE = 10   # 精細 (還是覺得沒力就改成 15)
STEP_NORMAL = 30 # 正常
STEP_FAST = 80   # 快速

current_step = STEP_NORMAL 

def update_servos():
    """寫入數值到馬達"""
    for name, pin in MOTORS.items():
        # 安全限制
        if current_pos[name] < 500: current_pos[name] = 500
        if current_pos[name] > 2500: current_pos[name] = 2500
        pi.set_servo_pulsewidth(pin, current_pos[name])

def draw_interface(stdscr):
    """繪製介面 (只負責畫圖，不負責邏輯)"""
    stdscr.erase()
    stdscr.addstr(0, 0, "=== MeArm 極速校正工具 v2 ===", curses.A_BOLD)
    stdscr.addstr(1, 0, "🚀 已優化：無延遲 / 高扭力模式")
    
    stdscr.addstr(3, 0, "[控制按鍵]")
    stdscr.addstr(4, 2, "⬅️ ➡️   : 底座 (Base)")
    stdscr.addstr(5, 2, "⬆️ ⬇️   : 肩膀 (Shoulder) - 最吃力")
    stdscr.addstr(6, 2, "W / S   : 手肘 (Elbow)")
    stdscr.addstr(7, 2, "O / P   : 夾爪 (Gripper)")
    
    speed_str = "正常 (30)"
    if current_step == STEP_FINE: speed_str = "精細 (10)"
    if current_step == STEP_FAST: speed_str = "極速 (80)"
    
    stdscr.addstr(9, 2, f"1/2/3 切換速度: 目前 [{speed_str}]")
    
    stdscr.addstr(11, 0, "=== 記錄這些數值 ===", curses.A_REVERSE)
    row = 13
    for name, val in current_pos.items():
        stdscr.addstr(row, 2, f"{name:<10}: {val}")
        row += 1
    
    stdscr.addstr(row+1, 0, "按 'Q' 離開")
    stdscr.refresh()

def main(stdscr):
    global current_step
    
    # 設置 curses
    curses.curs_set(0)
    stdscr.nodelay(1) # 非阻塞模式
    
    # 先歸位
    update_servos()
    draw_interface(stdscr)

    while True:
        # 1. 讀取按鍵
        key = stdscr.getch()

        # 如果沒按鍵，就休息一下避免吃滿 CPU，但時間要極短
        if key == -1:
            time.sleep(0.02) 
            continue

        # 2. 處理邏輯
        needs_redraw = True # 只有按鍵時才重畫介面

        if key == ord('q'): break
        
        # 速度切換
        elif key == ord('1'): current_step = STEP_FINE
        elif key == ord('2'): current_step = STEP_NORMAL
        elif key == ord('3'): current_step = STEP_FAST

        # 動作控制
        elif key == curses.KEY_LEFT:  current_pos['Base'] += current_step
        elif key == curses.KEY_RIGHT: current_pos['Base'] -= current_step
        elif key == curses.KEY_UP:    current_pos['Shoulder'] -= current_step
        elif key == curses.KEY_DOWN:  current_pos['Shoulder'] += current_step
        elif key == ord('w'): current_pos['Elbow'] -= current_step
        elif key == ord('s'): current_pos['Elbow'] += current_step
        elif key == ord('o'): current_pos['Gripper'] -= current_step
        elif key == ord('p'): current_pos['Gripper'] += current_step
        else:
            needs_redraw = False # 無效按鍵不重畫

        # 3. 執行與畫面更新
        if needs_redraw:
            update_servos()
            draw_interface(stdscr)
        
        # 🔥【關鍵修改】清除輸入緩衝區 🔥
        # 這行會把積壓在佇列裡的按鍵全部丟掉，確保下一圈讀到的是「現在」的狀態
        curses.flushinp()

    # 結束時放鬆馬達
    for pin in MOTORS.values():
        pi.set_servo_pulsewidth(pin, 0)

try:
    curses.wrapper(main)
except KeyboardInterrupt:
    pi.stop()
