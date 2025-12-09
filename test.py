import curses
import pigpio
import time
import config

# 初始化 pigpio
pi = pigpio.pi()
if not pi.connected:
    print("❌ 無法連接 pigpio，請執行 'sudo pigpiod'")
    exit()

# === 關鍵修正：確保這裡的 Keys 和下面 current_pos 的 Keys 完全一致 ===
MOTORS = {
    'Base': config.PIN_BASE,
    'Shoulder': config.PIN_SHOULDER,
    'Elbow': config.PIN_ELBOW,
    'Gripper': config.PIN_GRIPPER
}

current_pos = {
    'Base': 1420,
    'Shoulder': 1500,
    'Elbow': 1800,
    'Gripper': config.GRIPPER_OPEN
}

# 步進值設定
STEP_FINE = 10
STEP_NORMAL = 30
STEP_FAST = 80
current_step = STEP_NORMAL 

def update_servos():
    """寫入數值到馬達"""
    for name, pin in MOTORS.items():
        # 這裡會用 name 去 current_pos 找數值，所以 name 必須完全一樣
        if name not in current_pos:
            continue
            
        # 安全限制
        if current_pos[name] < 500: current_pos[name] = 500
        if current_pos[name] > 2500: current_pos[name] = 2500
        
        pi.set_servo_pulsewidth(pin, current_pos[name])

def draw_interface(stdscr):
    stdscr.erase()
    stdscr.addstr(0, 0, "=== MeArm Calibrate Tool v3 ===", curses.A_BOLD)
    
    stdscr.addstr(2, 0, "[Controls]")
    stdscr.addstr(3, 2, "Left/Right : Base")
    stdscr.addstr(4, 2, "Up/Down    : Shoulder")
    stdscr.addstr(5, 2, "W / S      : Elbow")
    stdscr.addstr(6, 2, "O / P      : Gripper")
    
    # 顯示目前速度
    speed_txt = "NORMAL"
    if current_step == STEP_FINE: speed_txt = "FINE"
    if current_step == STEP_FAST: speed_txt = "FAST"
    stdscr.addstr(8, 2, f"1/2/3 Speed: [{speed_txt} ({current_step})]")
    
    # 顯示數值
    stdscr.addstr(10, 0, "=== Current Values (Save These!) ===", curses.A_REVERSE)
    row = 12
    for name, val in current_pos.items():
        stdscr.addstr(row, 2, f"{name:<10}: {val}")
        row += 1
    
    stdscr.addstr(row+1, 0, "Press 'Q' to Quit")
    stdscr.refresh()

def main(stdscr):
    global current_step
    
    curses.curs_set(0)
    stdscr.nodelay(1)
    
    update_servos()
    draw_interface(stdscr)

    while True:
        key = stdscr.getch()

        if key == -1:
            time.sleep(0.02)
            continue

        needs_redraw = True

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
            needs_redraw = False

        if needs_redraw:
            update_servos()
            draw_interface(stdscr)
        
        curses.flushinp()

    # 結束時關閉馬達
    for pin in MOTORS.values():
        pi.set_servo_pulsewidth(pin, 0)

try:
    curses.wrapper(main)
except KeyboardInterrupt:
    pi.stop()
