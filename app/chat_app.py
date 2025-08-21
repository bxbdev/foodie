"""
整合後的 RAG 聊天 API - 使用新的架構
"""
import json
import asyncio
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 使用新的架構導入
from services.session_manager import session_manager
from services.rag_service import rag_service


app = FastAPI(title="RAG 聊天 API", description="智能客服聊天系統", version="1.0.0")


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
            
            # 執行 RAG 查詢
            response = chat_engine.chat(request.message)
            
            # 模擬串流效果（將回答分段發送）
            answer = response.response
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