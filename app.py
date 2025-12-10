from flask import Flask, render_template, request, jsonify
import pigpio
import time
import socket
import config  # 讀取你的設定檔 (config.py)

# 嘗試匯入 QR Code 庫 (如果沒裝也不會報錯，只是不顯示圖片)
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

app = Flask(__name__)

# === 1. 初始化 pigpio 連線 ===
pi = pigpio.pi()
if not pi.connected:
    print("❌ 錯誤：無法連接 pigpio daemon，請務必先執行 'sudo pigpiod'")
    # 我們不在此 exit，以免網頁伺服器無法啟動，但馬達將不會有反應
else:
    print("✅ pigpio 連線成功")

# === 2. 記錄目前狀態 (初始化為 Home) ===
# 這裡會讀取 config.py 的 HOME_POS，確保網頁顯示與實際一致
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

# ========================
#    馬達控制核心函式
# ========================

def move_servo(axis, val):
    """
    安全移動馬達 (包含使用者定義的極限保護)
    """
    global current_pos
    
    # --- 安全限位保護 (Safety Guards) ---
    # 根據你的機器特性進行防呆處理

    if axis == 'elbow':
        # 你說：1700 是往後極限，不能再小了
        if val < 1700: 
            print(f"⚠️ 警告：Elbow 試圖過度後縮 ({val})，強制修正為 1700")
            val = 1700
        # 你說：2300 是往前極限
        if val > 2300: val = 2300

    elif axis == 'shoulder':
        # 你說：1000 是降下來(低)，2200 是去抓取(更低)，1500 是垂直
        # 所以範圍我們要開大一點，讓它可以去抓地板的東西
        if val < 800: val = 800
        if val > 2400: val = 2400 # 開到 2400 以允許 2200 的動作

    elif axis == 'base':
        # 底座通常範圍較大
        if val < 500: val = 500
        if val > 2500: val = 2500
        
    elif axis == 'gripper':
        # 夾爪限制在 config 設定的範圍內稍微寬裕一點
        if val < 500: val = 500
        if val > 2500: val = 2500

    # --- 執行移動 ---
    if pi.connected:
        pi.set_servo_pulsewidth(PINS[axis], val)
    
    # --- 更新記憶位置 ---
    current_pos[axis] = val

def slow_move_to(target_pos_dict):
    """
    (自動模式專用) 
    依序移動三個軸，且動作放慢，確保安全與穩定
    """
    # 1. 移動底座
    move_servo('base', target_pos_dict['base'])
    time.sleep(2)  # [安全延遲] 等待 2 秒
    
    # 2. 移動肩膀
    move_servo('shoulder', target_pos_dict['shoulder'])
    time.sleep(2)  # [安全延遲] 等待 2 秒
    
    # 3. 移動手肘
    move_servo('elbow', target_pos_dict['elbow'])
    time.sleep(2)  # [安全延遲] 等待 2 秒

# ========================
#        Web 路由
# ========================

@app.route('/')
def index():
    return render_template('index.html')

# 功能 1: 手機手動遙控 API
@app.route('/move', methods=['POST'])
def manual_move():
    data = request.json
    axis = data.get('axis')
    step = int(data.get('step'))
    
    if axis in current_pos:
        # 計算目標位置
        new_val = current_pos[axis] + step
        # 執行移動 (move_servo 會處理限位)
        move_servo(axis, new_val)
        return jsonify({"status": "success", "val": new_val})
    
    return jsonify({"status": "error"}), 400

# 功能 2: 自動堆疊 API
@app.route('/auto_stack', methods=['POST'])
def auto_stack():
    print("🤖 [Auto] 收到指令，開始自動堆疊...")
    
    try:
        # 1. 回正 (Home)
        print(" -> 回歸原點")
        move_servo('gripper', config.GRIPPER_OPEN)
        slow_move_to(config.HOME_POS)
        
        # 2. 去抓取 (Pickup)
        print(" -> 移動至供料區")
        slow_move_to(config.PICKUP_HOVER) # 上方準備
        slow_move_to(config.PICKUP_DOWN)  # 下降抓取
        time.sleep(1) # 等穩
        
        print(" -> 夾取！")
        move_servo('gripper', config.GRIPPER_CLOSE) # 夾緊
        time.sleep(1)
        
        print(" -> 抬起")
        slow_move_to(config.PICKUP_HOVER) # 抬起
        
        # 3. 去放置 (Place)
        print(" -> 移動至堆疊區")
        slow_move_to(config.PLACE_HOVER)  # 上方準備
        slow_move_to(config.PLACE_DOWN)   # 下降放置
        time.sleep(1)
        
        print(" -> 鬆開")
        move_servo('gripper', config.GRIPPER_OPEN) # 鬆開
        time.sleep(1)
        
        print(" -> 抬起離開")
        slow_move_to(config.PLACE_HOVER)  # 抬起離開
        
        # 4. 回家
        print(" -> 任務完成，回家")
        slow_move_to(config.HOME_POS)
        
        return jsonify({"status": "completed"})
        
    except Exception as e:
        print(f"❌ 自動堆疊發生錯誤: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ========================
#      主程式進入點
# ========================
if __name__ == '__main__':
    
    # 取得本機 IP (用於顯示 QR Code)
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    host_ip = get_ip()
    url = f"http://{host_ip}:5000"

    print("\n" + "="*40)
    print("🚀 MeArm 機器人控制系統啟動中...")
    print("⚠️  警告：馬達將開始依序歸位，請保持淨空！")
    print("="*40)

    # === [安全啟動邏輯] ===
    # 依序歸位，中間休息，防止電源過載或暴衝
    
    print("1. 正在歸位：底座 (Base)...")
    move_servo('base', config.HOME_POS['base'])
    time.sleep(2) 
    
    print("2. 正在歸位：肩膀 (Shoulder)...")
    move_servo('shoulder', config.HOME_POS['shoulder'])
    time.sleep(2) 
    
    print("3. 正在歸位：手肘 (Elbow)...")
    move_servo('elbow', config.HOME_POS['elbow'])
    time.sleep(2) 
    
    print("4. 初始化夾爪...")
    move_servo('gripper', config.GRIPPER_OPEN)
    time.sleep(1)
    
    print("\n" + "="*40)
    print("✅ 系統就緒！ Web Server 已啟動")
    print(f"🔗 連線網址: {url}")
    print("👇 請掃描 QR Code 連線 👇")
    print("="*40)
    
    # === 顯示 QR Code ===
    if HAS_QR:
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        try:
            qr.print_ascii(invert=True)
        except:
            # 有些終端機不支援 invert，改用一般模式
            qr.print_ascii()
    else:
        print("(未安裝 qrcode 套件，無法顯示圖碼，請手動輸入網址)")
    
    print("="*40 + "\n")
    
    # 啟動 Flask 伺服器
    app.run(host='0.0.0.0', port=5000, debug=True)
