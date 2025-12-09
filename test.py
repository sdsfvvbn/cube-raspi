import serial
import time

# 請將這裡改成你正確的 COM Port
COM_PORT = 'COM3'  
BAUD_RATE = 9600

try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # 等待 Arduino 重啟連線
    
    print("連線成功，準備測試...")
    
    # 測試動作：送出 90 度 (假設你的邏輯是送角度)
    # 記得加上 \n
    command = "90\n" 
    ser.write(command.encode('utf-8'))
    print(f"已發送: {command}")
    
    ser.close()
    print("測試結束")

except Exception as e:
    print(f"發生錯誤: {e}")
