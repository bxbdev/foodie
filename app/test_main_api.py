import requests
import json

def test_main_api():
    base_url = "http://localhost:8000"
    
    print("=== 測試 main.py 版本的 API ===")
    
    # 1. 測試根路徑
    print("\n1. 測試根路徑...")
    response = requests.get(f"{base_url}/")
    print(f"   GET / -> {response.status_code}: {response.json()}")
    
    # 2. 測試會話創建
    print("\n2. 測試會話創建...")
    response = requests.post(f"{base_url}/api/v1/chat/session")
    print(f"   POST /api/v1/chat/session -> {response.status_code}: {response.json()}")
    
    # 3. 測試串流聊天
    print("\n3. 測試串流聊天...")
    chat_data = {"message": "測試訊息"}
    try:
        response = requests.post(
            f"{base_url}/api/v1/chat/stream",
            json=chat_data,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=10
        )
        print(f"   POST /api/v1/chat/stream -> {response.status_code}")
        
        if response.status_code == 200:
            print("   SSE 流回應:")
            count = 0
            for line in response.iter_lines():
                if count >= 3:  # 只顯示前3行
                    break
                if line:
                    decoded_line = line.decode('utf-8')
                    print(f"     {decoded_line}")
                    count += 1
        else:
            print(f"   錯誤: {response.text}")
            
    except Exception as e:
        print(f"   異常: {e}")

if __name__ == "__main__":
    test_main_api()