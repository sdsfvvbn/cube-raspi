from flask import Flask, render_template, request
import pigpio
import time
import config  # 匯入剛剛的設定檔

app = Flask(__name__)

# 初始化 pigpio
pi = pigpio.pi()
if not pi.connected:
    print("無法連接到 pigpio daemon，請先執行 'sudo pigpiod'")
    exit()

# 目前馬達的位置紀錄 (全域變數)
current_pos = {
    'base': config.HOME_POS['base'],
    'shoulder': config.HOME_POS['shoulder'],
    'elbow': config.HOME_POS['elbow'],
    'gripper': config.GRIPPER_OPEN
}

def set_servo(pin, pulse):
    """直接設定馬達 (用於夾爪或快速歸位)"""
    pi.set_servo_pulsewidth(pin, pulse)

def slow_move(target_base, target_shoulder, target_elbow, speed=0.005):
    """
    平滑移動函式：解決 README 提到的抖動問題
    同步移動三個軸，避免單軸移動造成路徑怪異
    """
    global current_pos
    
    # 簡單的線性插值邏輯 (Step-by-step)
    # 這裡為了簡化，我們先依序移動軸，實際專案可做多執行緒同步
    # 1. 移動底座
    move_single_axis(config.PIN_BASE, 'base', target_base, speed)
    # 2. 移動肩膀
    move_single_axis(config.PIN_SHOULDER, 'shoulder', target_shoulder, speed)
    # 3. 移動手肘
    move_single_axis(config.PIN_ELBOW, 'elbow', target_elbow, speed)

def move_single_axis(pin, axis_name, target, speed):
    """單軸平滑移動"""
    start = current_pos[axis_name]
    step = 10 if target > start else -10
    
    for pulse in range(start, target, step):
        pi.set_servo_pulsewidth(pin, pulse)
        time.sleep(speed) # 控制速度
    
    # 確保最後準確到達目標
    pi.set_servo_pulsewidth(pin, target)
    current_pos[axis_name] = target

def soft_start():
    """軟啟動：解決 README 提到的啟動電流暴衝問題"""
    print("執行軟啟動...")
    servos = [
        (config.PIN_BASE, config.HOME_POS['base']),
        (config.PIN_SHOULDER, config.HOME_POS['shoulder']),
        (config.PIN_ELBOW, config.HOME_POS['elbow']),
        (config.PIN_GRIPPER, config.GRIPPER_OPEN)
    ]
    
    for pin, val in servos:
        pi.set_servo_pulsewidth(pin, val)
        time.sleep(0.5) # 每顆馬達間隔 0.5 秒通電
    
    # 更新目前位置紀錄
    global current_pos
    current_pos = config.HOME_POS.copy()
    current_pos['gripper'] = config.GRIPPER_OPEN
    print("軟啟動完成，手臂就緒。")

# === 寫死的自動化流程 ===
def execute_stack_sequence():
    print("開始執行自動堆疊...")
    
    # 1. 回到 Home (確保安全)
    slow_move(config.HOME_POS['base'], config.HOME_POS['shoulder'], config.HOME_POS['elbow'])
    set_servo(config.PIN_GRIPPER, config.GRIPPER_OPEN)
    time.sleep(0.5)

    # 2. 移動到供料區上方 (Hover)
    print("移動至供料區上方...")
    slow_move(config.PICKUP_HOVER['base'], config.PICKUP_HOVER['shoulder'], config.PICKUP_HOVER['elbow'])
    
    # 3. 下降抓取
    print("下降抓取...")
    slow_move(config.PICKUP_DOWN['base'], config.PICKUP_DOWN['shoulder'], config.PICKUP_DOWN['elbow'])
    time.sleep(0.5)
    
    # 4. 夾緊 (快速動作)
    print("夾取積木！")
    set_servo(config.PIN_GRIPPER, config.GRIPPER_CLOSE)
    time.sleep(0.5)
    
    # 5. 抬起 (回到 Hover)
    print("抬起...")
    slow_move(config.PICKUP_HOVER['base'], config.PICKUP_HOVER['shoulder'], config.PICKUP_HOVER['elbow'])
    
    # 6. 移動到放置區上方
    print("搬運中...")
    slow_move(config.PLACE_HOVER['base'], config.PLACE_HOVER['shoulder'], config.PLACE_HOVER['elbow'])
    
    # 7. 下降放置
    print("放置積木...")
    slow_move(config.PLACE_DOWN['base'], config.PLACE_DOWN['shoulder'], config.PLACE_DOWN['elbow'])
    time.sleep(0.5)
    
    # 8. 鬆開夾爪
    print("鬆開...")
    set_servo(config.PIN_GRIPPER, config.GRIPPER_OPEN)
    time.sleep(0.5)
    
    # 9. 抬起並回 Home
    print("任務完成，回歸原點。")
    slow_move(config.PLACE_HOVER['base'], config.PLACE_HOVER['shoulder'], config.PLACE_HOVER['elbow'])
    slow_move(config.HOME_POS['base'], config.HOME_POS['shoulder'], config.HOME_POS['elbow'])

# === Web路由 ===

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_stacking():
    # 執行寫死的流程
    execute_stack_sequence()
    return "OK"

if __name__ == '__main__':
    try:
        soft_start() # 程式啟動時先執行軟啟動
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # 程式結束時關閉 PWM (放鬆馬達)
        pi.set_servo_pulsewidth(config.PIN_BASE, 0)
        pi.set_servo_pulsewidth(config.PIN_SHOULDER, 0)
        pi.set_servo_pulsewidth(config.PIN_ELBOW, 0)
        pi.set_servo_pulsewidth(config.PIN_GRIPPER, 0)
        pi.stop()
