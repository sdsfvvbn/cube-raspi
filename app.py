from flask import Flask, render_template, request, jsonify
import pigpio
import time
import config  # 讀取上面的設定檔

app = Flask(__name__)

# === 初始化 pigpio ===
pi = pigpio.pi()
if not pi.connected:
    print("❌ 錯誤：無法連接 pigpio daemon，請先執行 'sudo pigpiod'")
    # 為了不讓程式直接掛掉，我們只印錯誤，但實際操作會沒反應
else:
    print("✅ pigpio 連線成功")

# === 記錄目前位置 (初始化為 Home) ===
current_pos = {
    'base': config.HOME_POS['base'],
    'shoulder': config.HOME_POS['shoulder'],
    'elbow': config.HOME_POS['elbow'],
    'gripper': config.GRIPPER_OPEN
}

# 腳位對應表
PINS = {
    'base': config.PIN_BASE,
    'shoulder': config.PIN_SHOULDER,
    'elbow': config.PIN_ELBOW,
    'gripper': config.PIN_GRIPPER
}

# app.py 的 move_servo 函式 (請覆蓋原本的)

def move_servo(axis, val):
    """安全移動馬達 (包含使用者定義的極限保護)"""
    global current_pos
    
    # === 1. 安全限位保護 (Safety Guards) ===
    # 這是根據你的描述特別加入的「防呆機制」
    
    if axis == 'elbow':
        # 你說：1700 是往後極限，不能再小了
        if val < 1700: 
            print(f"⚠️ 警告：Elbow 試圖移動到 {val}，已強制修正為 1700")
            val = 1700
        # 你說：2300 是往前
        if val > 2300: val = 2300

    elif axis == 'shoulder':
        # 你說：1000 是降下來，1700 是抬起來
        if val < 900: val = 900   # 留一點緩衝
        if val > 2200: val = 2200 # 防止抬太高卡住

    elif axis == 'base':
        # 底座通常 500~2500 都可以，但你可以自己縮小範圍
        if val < 500: val = 500
        if val > 2500: val = 2500

    # === 2. 執行移動 ===
    if pi.connected:
        pi.set_servo_pulsewidth(PINS[axis], val)
    
    # === 3. 更新記憶 ===
    current_pos[axis] = val

def slow_move_to(target_pos_dict):
    """
    (自動模式專用) 
    依序移動三個軸，且動作放慢，確保安全
    """
    # 1. 移動底座
    move_servo('base', target_pos_dict['base'])
    time.sleep(2)  # <--- [安全延遲] 這裡改成等待 2 秒
    
    # 2. 移動肩膀
    move_servo('shoulder', target_pos_dict['shoulder'])
    time.sleep(2)  # <--- [安全延遲] 等待 2 秒
    
    # 3. 移動手肘
    move_servo('elbow', target_pos_dict['elbow'])
    time.sleep(2)  # <--- [安全延遲] 等待 2 秒

# ========================
#        Web 路由
# ========================

@app.route('/')
def index():
    return render_template('index.html')

# 功能 1: 手機手動遙控
@app.route('/move', methods=['POST'])
def manual_move():
    data = request.json
    axis = data.get('axis')
    step = int(data.get('step'))
    
    if axis in current_pos:
        new_val = current_pos[axis] + step
        move_servo(axis, new_val)
        return jsonify({"status": "success", "val": new_val})
    return jsonify({"status": "error"}), 400

# 功能 2: 自動堆疊 (寫死的流程)
@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    print("🤖 收到指令，開始自動堆疊...")
    
    # 1. 回正
    move_servo('gripper', config.GRIPPER_OPEN)
    slow_move_to(config.HOME_POS)
    
    # 2. 去抓取
    slow_move_to(config.PICKUP_HOVER) # 移到上方
    slow_move_to(config.PICKUP_DOWN)  # 下降
    time.sleep(1)
    move_servo('gripper', config.GRIPPER_CLOSE) # 夾緊
    time.sleep(1)
    slow_move_to(config.PICKUP_HOVER) # 抬起
    
    # 3. 去放置
    slow_move_to(config.PLACE_HOVER)  # 移到上方
    slow_move_to(config.PLACE_DOWN)   # 下降
    time.sleep(1)
    move_servo('gripper', config.GRIPPER_OPEN) # 鬆開
    time.sleep(1)
    slow_move_to(config.PLACE_HOVER)  # 抬起離開
    
    # 4. 回家
    slow_move_to(config.HOME_POS)
    
    return jsonify({"status": "completed"})

# ========================
#      主程式進入點
# ========================
if __name__ == '__main__':
    print("\n🚀 系統啟動程序開始...")
    print("⚠️  警告：馬達將開始歸位，請確保手臂周圍淨空！")
    print("---------------------------------------------")

    # [安全啟動邏輯] 依序歸位，中間休息 2.5 秒
    
    print("1. 正在歸位：底座 (Base)...")
    move_servo('base', config.HOME_POS['base'])
    time.sleep(2.5) 
    
    print("2. 正在歸位：肩膀 (Shoulder)...")
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(2.5) 
    
    print("3. 正在歸位：手肘 (Elbow)...")
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(2.5) 
    
    print("4. 初始化夾爪...")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(1)
    
    print("---------------------------------------------")
    print("✅ 歸位完成，Web Server 啟動中...")
    print(f"🔗 請用手機瀏覽器開啟: http://[樹莓派IP]:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)


