# arm_driver.py - 機械手臂驅動核心
import pigpio
import time
import config  # 匯入上面的設定檔

class MeArm:
    def __init__(self):
        # 連線到 pigpio 服務
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise Exception("❌ 錯誤：pigpiod 服務沒開！請執行 sudo systemctl start pigpiod")
        
        print("✅ 機械手臂驅動模組已啟動")
        # 剛啟動時，建議先放鬆所有馬達，避免暴衝
        self.relax()

    def set_pulse(self, pin, pwm_value):
        """ 底層函式：直接送出 PWM 訊號 """
        self.pi.set_servo_pulsewidth(pin, int(pwm_value))

    def _map_percent(self, percent, limits):
        """ 數學小工具：把 0~100% 換算成 PWM 範圍 """
        # 限制輸入在 0~100 之間，防止轉過頭燒掉馬達
        percent = max(0, min(100, percent))
        
        min_pwm = limits[0]
        max_pwm = limits[1]
        
        # 線性插值公式 (把百分比變成脈衝)
        return min_pwm + (max_pwm - min_pwm) * (percent / 100.0)

    # --- 動作指令區 ---

    def move_base(self, percent):
        """ 移動底座 (0% ~ 100%) """
        target_pwm = self._map_percent(percent, config.LIMIT_BASE)
        self.set_pulse(config.PIN_BASE, target_pwm)

    def move_shoulder(self, percent):
        """ 移動左臂/肩 (0% ~ 100%) """
        target_pwm = self._map_percent(percent, config.LIMIT_SHOULDER)
        self.set_pulse(config.PIN_SHOULDER, target_pwm)

    def move_middle(self, percent):
        """ 移動右臂/肘 (0% ~ 100%) """
        target_pwm = self._map_percent(percent, config.LIMIT_ELBOW)
        self.set_pulse(config.PIN_ELBOW, target_pwm)

    def move_gripper(self, percent):
        """ 
        控制夾爪 
        0%   = 張開 (1600)
        100% = 閉合 (2350)
        """
        target_pwm = self._map_percent(percent, config.LIMIT_GRIPPER)
        self.set_pulse(config.PIN_GRIPPER, target_pwm)

    def relax(self):
        """ 放鬆所有馬達 (停止出力，省電模式) """
        for pin in [config.PIN_BASE, config.PIN_SHOULDER, config.PIN_ELBOW, config.PIN_GRIPPER]:
            self.set_pulse(pin, 0)

    def close(self):
        """ 關閉程式時呼叫 """
        self.relax()
        self.pi.stop()

# --- 測試區 (直接執行這個檔案時會跑這裡) ---
if __name__ == "__main__":
    arm = MeArm()
    try:
        print("1. 底座轉到中間 (50%)...")
        arm.move_base(50)
        time.sleep(1)

        print("2. 左臂抬起 (50%)...")
        arm.move_shoulder(50)
        time.sleep(1)
        
        print("3. 右臂(Middle) 移動 (50%)...")
        arm.move_middle(50)
        time.sleep(1)

        print("4. 夾爪測試：開(0) -> 合(100)")
        arm.move_gripper(0)   # 張開
        time.sleep(1)
        arm.move_gripper(100) # 閉合 (夾緊)
        time.sleep(1)
        arm.move_gripper(0)   # 再張開
        time.sleep(1)

        print("測試完成！馬達放鬆。")
        
    except KeyboardInterrupt:
        print("\n中斷測試")
    finally:
        arm.close()