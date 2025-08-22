"""
整合後的 RAG 聊天 API - 使用新的架構
"""
import json
import asyncio
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 使用新的架構導入
from services.session_manager import session_manager
from services.rag_service import rag_service


app = FastAPI(title="RAG 聊天 API", description="智能客服聊天系統", version="1.0.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源，生產環境應該指定具體域名
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有 HTTP 方法
    allow_headers=["*"],  # 允許所有標頭
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat/session", response_model=SessionResponse)
async def create_chat_session():
    """創建新的聊天會話"""
    session_id = session_manager.create_session()
    return SessionResponse(
        session_id=session_id,
        message="會話已創建，可以開始聊天"
    )


def is_simple_greeting_or_test(message: str) -> bool:
    """檢查是否為簡單的問候或測試輸入"""
    message = message.strip().lower()
    simple_inputs = {
        "測試", "test", "嗨", "hi", "hello", "你好", "哈囉", "halo",
        "在嗎", "在不在", "有人嗎", "可以聊天嗎", "可以說話嗎",
        "!", "？", "?", "嘿", "hey", "yo", "哇", "wow"
    }
    return message in simple_inputs or len(message) <= 3

def is_return_related(message: str) -> bool:
    """判斷消息是否與退貨相關"""
    message = message.strip().lower()
    
    # 退貨相關關鍵詞
    return_keywords = {
        "退貨", "退款", "退回", "換貨", "退換", "不滿意", "有問題", "壞了", "破損",
        "瑕疵", "不合適", "尺寸不對", "顏色不對", "收到錯誤", "想退",
        "申請退", "辦理退", "如何退", "退貨流程", "退貨期限", "退貨條件",
        "退貨政策", "退貨規定", "可以退嗎", "能退嗎", "退貨費用"
    }
    
    return any(keyword in message for keyword in return_keywords)

def get_simple_response(message: str) -> str:
    """為簡單輸入提供合適的回應"""
    message = message.strip().lower()
    
    if message in ["測試", "test"]:
        return "系統運行正常！有什麼關於退貨政策的問題我可以幫您解答嗎？"
    elif message in ["嗨", "hi", "hello", "你好", "哈囉", "halo"]:
        return "您好！我是客服助理，專門協助處理退貨相關問題。請問有什麼需要幫助的嗎？"
    elif message in ["在嗎", "在不在", "有人嗎"]:
        return "是的，我在線上！有什麼退貨問題需要協助嗎？"
    else:
        return "您好！我是智能客服助理，專門回答退貨政策相關問題。請具體描述您的問題，我會盡力為您解答。"

def get_general_llm_response(message: str) -> str:
    """使用LLM直接回答非退貨相關問題"""
    # 導入Ollama LLM
    from services.rag_service import rag_service
    from llama_index.core import Settings
    
    llm = Settings.llm
    
    prompt = f"""你是一個友善的智能助理。請直接回答用戶的問題，但要提醒用戶我主要專長是協助退貨相關問題。

用戶問題：{message}

請提供簡潔有用的回答，並在最後提及如果有退貨相關問題可以詢問我。"""
    
    response = llm.complete(prompt)
    return response.text


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE 串流聊天端點"""
    
    # 處理會話ID
    session_id = request.session_id
    if not session_id:
        session_id = session_manager.create_session()
    
    # 獲取或創建聊天引擎
    chat_engine = session_manager.get_chat_engine(session_id)
    if not chat_engine:
        # 為這個會話創建新的聊天引擎
        memory = session_manager.get_or_create_memory(session_id)
        chat_engine = rag_service.create_chat_engine(memory)
        session_manager.set_chat_engine(session_id, chat_engine)
    
    async def generate_response():
        """生成 SSE 串流回應"""
        try:
            # 發送會話ID（如果是新創建的）
            if request.session_id != session_id:
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            
            # 發送開始信號
            yield f"data: {json.dumps({'type': 'start', 'message': '正在思考...'})}\n\n"
            
            # 三層智能判斷：1) 簡單問候 2) 退貨相關 3) 一般問題
            if is_simple_greeting_or_test(request.message):
                # 第一層：簡單問候語，直接回應
                answer = get_simple_response(request.message)
            elif is_return_related(request.message):
                # 第二層：退貨相關問題，使用RAG檢索
                response = chat_engine.chat(request.message)
                answer = response.response
            else:
                # 第三層：非退貨問題，使用LLM直接回答
                answer = get_general_llm_response(request.message)
            
            # 統一的串流效果（將回答分段發送）
            words = answer.split()
            current_text = ""
            for i, word in enumerate(words):
                current_text += word + " "
                
                # 每5個詞發送一次
                if (i + 1) % 5 == 0 or i == len(words) - 1:
                    yield f"data: {json.dumps({'type': 'content', 'content': current_text.strip()})}\n\n"
                    await asyncio.sleep(0.1)  # 模擬思考時間
            
            # 發送完成信號
            yield f"data: {json.dumps({'type': 'done', 'message': '回答完成'})}\n\n"
            
        except Exception as e:
            # 發送錯誤信息
            yield f"data: {json.dumps({'type': 'error', 'message': f'發生錯誤: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


@app.get("/api/chat/sessions")
async def get_session_info():
    """獲取會話統計信息"""
    # 清理過期會話
    cleaned = session_manager.cleanup_expired_sessions()
    
    return {
        "active_sessions": session_manager.get_session_count(),
        "cleaned_sessions": cleaned
    }


@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str):
    """刪除指定會話"""
    deleted = session_manager.delete_session(session_id)
    return {
        "deleted": deleted,
        "message": "會話已刪除" if deleted else "會話不存在"
    }


@app.get("/api/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "rag_service": "ready",
        "active_sessions": session_manager.get_session_count()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)