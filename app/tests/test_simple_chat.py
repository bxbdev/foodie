import requests
import json

def test_health():
    print("Testing health endpoint...")
    response = requests.get("http://localhost:8000/api/health")
    print(f"Health: {response.json()}")

def test_create_session():
    print("\nCreating session...")
    response = requests.post("http://localhost:8000/api/chat/session")
    session_data = response.json()
    print(f"Session: {session_data}")
    return session_data.get('session_id')

def test_simple_chat():
    print("\nTesting simple chat...")
    
    # Test data
    chat_data = {
        "message": "商品已經拆封的話，還能夠退貨嗎？"
    }
    
    # Send request
    try:
        response = requests.post(
            "http://localhost:8000/api/chat/stream",
            json=chat_data,
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        
        print(f"Status: {response.status_code}")
        print("Response:")
        
        # Read SSE stream
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data = json.loads(decoded_line[6:])
                    print(f"  {data}")
                    if data.get('type') == 'done':
                        break
                        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_health()
    test_create_session() 
    test_simple_chat()