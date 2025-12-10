# app.py - MeArm 機械手臂控制核心 (最終完整版)
from flask import Flask, render_template, request, jsonify
import pigpio
import time
import socket
import config  # 讀取你的 config.py

# 嘗試匯入 QR Code 套件 (沒裝也不會報錯)
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

app = Flask(__name__)

# ==========================================
# 1. 硬體初始化
# ==========================================
pi = pigpio.pi()
if not pi.connected:
    print("❌ 錯誤：無法連接 pigpio daemon，請務必先執行 'sudo pigpiod'")
else:
    print("✅ pigpio 連線成功")

# 記錄目前位置 (初始化為 config 的預設值)
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

# ==========================================
# 2. 馬達控制核心 (含安全限位)
# ==========================================
def move_servo(axis, val):
    """
    移動馬達並寫入 PWM，包含針對你機器的安全限位保護
    """
    global current_pos
    
    # --- 安全限位保護 (Safety Guards) ---
    
    if axis == 'elbow':
        # 上限開到 2400 以確保能到達你的 2300 極限
        if val < 1700: val = 1700
        if val > 2400: val = 2400 

    elif axis == 'shoulder':
        # 下限開低一點 (800) 以便去抓地上的積木 (1000)
        if val < 800: val = 800
        if val > 2400: val = 2400

    elif axis == 'base':
        if val < 500: val = 500
        if val > 2500: val = 2500

    elif axis == 'gripper':
        if val < 500: val = 500
        if val > 2500: val = 2500

    # --- 執行移動 ---
    if pi.connected:
        pi.set_servo_pulsewidth(PINS[axis], val)
    
    # --- 更新記憶 ---
    current_pos[axis] = val

def relax_all_motors():
    """任務結束後放鬆所有馬達，避免發熱"""
    print("😴 放鬆馬達訊號...")
    if pi.connected:
        for p in PINS.values():
            pi.set_servo_pulsewidth(p, 0)

# ==========================================
# 3. 核心搬運邏輯 (Lift-then-Turn)
# ==========================================
def perform_stacking(target_hover, target_down):
    """
    執行單次搬運任務：從供料區 -> 目標區
    嚴格遵守「抓取 -> 原地抬高 -> 旋轉 -> 放置」順序
    """
    
    # === A. 歸位 & 去供料區 (Pickup) ===
    # 1. 安全歸位
    move_servo('gripper', config.GRIPPER_OPEN)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.8)
    move_servo('base', config.PICKUP_HOVER['base']) # 直接轉向供料區
    time.sleep(1.5)
    
    # 2. 伸出手臂 (Hover)
    move_servo('shoulder', config.PICKUP_HOVER['shoulder'])
    move_servo('elbow', config.PICKUP_HOVER['elbow'])
    time.sleep(1.5)
    
    # 3. 下降抓取 (Down)
    move_servo('elbow', config.PICKUP_DOWN['elbow'])
    time.sleep(0.5)
    move_servo('shoulder', config.PICKUP_DOWN['shoulder']) # 降到 1000
    time.sleep(1.2) # 等穩一點
    
    # 4. 夾取
    print("    ✊ 夾取")
    move_servo('gripper', config.GRIPPER_CLOSE)
    time.sleep(1)
    
    # === B. 搬運 (關鍵：先抬高，再轉向) ===
    
    # 1. 【原地抬高】 (Lift) - 安全關鍵
    print("    🔼 原地抬高 Shoulder...")
    move_servo('shoulder', 1500) 
    time.sleep(1)
    
    # 2. 【空中旋轉】 (Turn)
    print("    🔄 底座旋轉...")
    move_servo('base', target_hover['base'])
    time.sleep(1.5)
    
    # 3. 【調整手肘】
    move_servo('elbow', target_hover['elbow']) 
    time.sleep(1)

    # === C. 放置 (Place) ===
    print("    ⬇️ 下降放置")
    move_servo('shoulder', target_down['shoulder']) 
    time.sleep(1)
    
    print("    👐 鬆開")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(1)
    
    # === D. 撤退回家 ===
    print("    🏠 撤退")
    move_servo('shoulder', 1500) # 先抬高
    time.sleep(1)
    move_servo('elbow', 1700)    # 收手
    time.sleep(0.8)
    move_servo('base', config.HOME_POS['base']) # 回正
    time.sleep(1)

# ==========================================
# 4. Web 路由設定
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

# --- 功能 A: 手機手動微調 ---
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

# --- 功能 B: 夾爪一鍵到位 ---
@app.route('/set_gripper', methods=['POST'])
def set_gripper():
    data = request.json
    action = data.get('action') # 'open' or 'close'
    target_val = config.GRIPPER_CLOSE if action == 'close' else config.GRIPPER_OPEN
    move_servo('gripper', target_val)
    return jsonify({"status": "success"})

# --- 功能 C: 一鍵致中 ---
@app.route('/home', methods=['POST'])
def go_home():
    print("🏠 執行手動歸位...")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(0.5)
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(0.5)
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(0.5)
    move_servo('base', config.HOME_POS['base'])
    return jsonify({"status": "success"})

# --- 功能 D: 單一堆疊 ---
@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    print("🤖 [Auto] 執行：單一堆疊")
    try:
        perform_stacking(config.PLACE_HOVER, config.PLACE_DOWN)
        relax_all_motors() # 完成後放鬆
        return jsonify({"status": "completed"})
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return jsonify({"status": "error"}), 500

# --- 功能 E: 金字塔連續堆疊 (含補貨等待) ---
@app.route('/build_pyramid', methods=['POST'])
def build_pyramid():
    print("🏗️ [Auto] 啟動：金字塔連續模式")
    
    try:
        # 使用迴圈，依序處理每一顆積木
        for i, target in enumerate(config.PYRAMID_POSITIONS):
            block_num = i + 1
            print(f"\n=== 第 {block_num} 顆：{target['name']} ===")
            
            # 如果不是第 1 顆，代表剛搬完，需要等待補貨
            if block_num > 1:
                print("⏳ 等待補貨中 (4秒)...")
                time.sleep(4) # <--- 補貨時間
            
            perform_stacking(target['hover'], target['down'])
            print(f"✅ 第 {block_num} 顆完成")

        print("🎉 金字塔任務全部完成！")
        relax_all_motors() # 全部完成後放鬆
        return jsonify({"status": "completed", "message": "金字塔已完成"})
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        relax_all_motors() # 出錯也要放鬆
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 5. 主程式啟動點
# ==========================================
if __name__ == '__main__':
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    host_ip = get_ip()
    url = f"http://{host_ip}:5000"

    print("\n" + "="*45)
    print("🚀 MeArm 機器人系統啟動 (Ctrl+C 結束)")
    print("⚠️  注意：馬達開始歸位，請保持淨空！")
    print("="*45)

    try:
        # === 開機緩衝歸位 ===
        print("1. 底座歸位...")
        move_servo('base', config.HOME_POS['base'])
        time.sleep(1.5) 
        
        print("2. 肩膀歸位...")
        move_servo('shoulder', config.HOME_POS['shoulder'])
        time.sleep(1.5) 
        
        print("3. 手肘歸位...")
        move_servo('elbow', config.HOME_POS['elbow'])
        time.sleep(1.5) 
        
        print("4. 夾爪初始化...")
        move_servo('gripper', config.GRIPPER_OPEN)
        time.sleep(1)
        
        print("\n" + "="*45)
        print(f"✅ Web Server 已啟動！")
        print(f"🔗 連線網址: {url}")
        print("👇 請掃描 QR Code 連線 👇")
        print("="*45)
        
        if HAS_QR:
            qr = qrcode.QRCode()
            qr.add_data(url)
            qr.make(fit=True)
            try: qr.print_ascii(invert=True)
            except: qr.print_ascii()
        
        app.run(host='0.0.0.0', port=5000, debug=True)

    except KeyboardInterrupt:
        print("\n⛔ 程式停止，放鬆馬達...")
        relax_all_motors()
        pi.stop()
        print("✅ 已安全退出")
    finally:
        if pi.connected: pi.stop()
