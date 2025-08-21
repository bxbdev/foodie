"""
測試 RAG 聊天 API 的多用戶上下文隔離
"""
import asyncio
import aiohttp
import json


async def test_chat_session(session_name: str, messages: list):
    """測試單個聊天會話"""
    print(f"\n=== {session_name} 會話測試 ===")
    
    session_id = None
    
    async with aiohttp.ClientSession() as client:
        for i, message in enumerate(messages, 1):
            print(f"\n{session_name} Q{i}: {message}")
            
            # 準備請求數據
            request_data = {"message": message}
            if session_id:
                request_data["session_id"] = session_id
            
            try:
                # 發送 SSE 請求
                async with client.post(
                    "http://localhost:8000/api/v1/chat/stream",
                    json=request_data,
                    headers={"Accept": "text/event-stream"}
                ) as response:
                    
                    if response.status == 200:
                        full_response = ""
                        
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            
                            if line.startswith('data: '):
                                data = json.loads(line[6:])  # 移除 'data: ' 前綴
                                
                                if data['type'] == 'session_id':
                                    session_id = data['session_id']
                                    print(f"  會話ID: {session_id}")
                                
                                elif data['type'] == 'content':
                                    full_response = data['content']
                                
                                elif data['type'] == 'done':
                                    print(f"{session_name} A{i}: {full_response}")
                                    break
                                
                                elif data['type'] == 'error':
                                    print(f"錯誤: {data['message']}")
                                    break
                    else:
                        print(f"請求失敗: {response.status}")
                        
            except Exception as e:
                print(f"請求異常: {e}")
            
            # 短暫延遲
            await asyncio.sleep(1)


async def test_multiple_users():
    """測試多用戶並發聊天"""
    
    # 用戶A的對話流程 - 關於退貨
    user_a_messages = [
        "商品已經拆封的話，還能夠退貨嗎？",
        "我說的是外裝盒，商品本身只有塑膠袋套著",
        "所以我還是可以退貨對吧？"
    ]
    
    # 用戶B的對話流程 - 關於換貨  
    user_b_messages = [
        "我的商品有瑕疵，要怎麼換貨？",
        "需要寄到哪個地址？",
        "換貨有時間限制嗎？"
    ]
    
    # 並發執行兩個用戶的對話
    await asyncio.gather(
        test_chat_session("用戶A", user_a_messages),
        test_chat_session("用戶B", user_b_messages)
    )


async def test_session_info():
    """測試會話信息端點"""
    print("\n=== 會話統計信息 ===")
    
    async with aiohttp.ClientSession() as client:
        async with client.get("http://localhost:8000/api/v1/chat/sessions") as response:
            if response.status == 200:
                data = await response.json()
                print(f"活躍會話數: {data['active_sessions']}")
                print(f"清理會話數: {data['cleaned_sessions']}")
            else:
                print(f"請求失敗: {response.status}")


async def main():
    """主測試函數"""
    print("開始測試 RAG 聊天 API...")
    print("請確保 FastAPI 服務已在 http://localhost:8000 啟動")
    
    # 測試健康檢查
    async with aiohttp.ClientSession() as client:
        try:
            async with client.get("http://localhost:8000/") as response:
                if response.status == 200:
                    print("✅ API 服務運行正常")
                else:
                    print("❌ API 服務異常")
                    return
        except Exception as e:
            print(f"❌ 無法連接到 API 服務: {e}")
            return
    
    # 測試多用戶對話
    await test_multiple_users()
    
    # 查看會話統計
    await test_session_info()
    
    print("\n測試完成！")


if __name__ == "__main__":
    asyncio.run(main())