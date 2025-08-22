"""
RAG 聊天 API 端點
"""
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 導入我們的服務
from services.session_manager import session_manager
from services.rag_service import rag_service


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    with_greeting: bool = True  # 是否需要問候語


class SessionResponse(BaseModel):
    session_id: str
    message: str
    greeting: Optional[str] = None  # 初始問候語


def generate_greeting() -> str:
    """生成客服問候語"""
    import random
    
    greetings = [
        "您好！我是您的專屬客服助理，很高興為您服務！請問有什麼可以幫助您的呢？",
        "歡迎來到 Foodie！我是客服助理，隨時準備協助您處理各種問題。有什麼需要幫忙的嗎？",
        "您好！歡迎使用我們的服務！我可以幫您處理退貨、換貨或任何產品相關的問題。請告訴我您的需求！",
        "嗨！很開心見到您！我是您的貼心客服，專門協助處理訂單和產品問題。請問今天可以為您做什麼呢？",
        "您好！感謝您選擇 Foodie！我是客服助理，專業處理退貨、換貨等服務。有任何問題都可以問我哦！"
    ]
    
    return random.choice(greetings)


@router.post("/session", response_model=SessionResponse)
async def create_chat_session(request: CreateSessionRequest = CreateSessionRequest()):
    """創建新的聊天會話"""
    session_id = session_manager.create_session()
    
    greeting = None
    if request.with_greeting:
        greeting = generate_greeting()
    
    return SessionResponse(
        session_id=session_id,
        message="會話已創建，可以開始聊天",
        greeting=greeting
    )


@router.post("/stream")
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
            # 設置處理狀態
            session_manager.set_processing_status(session_id, True)
            session_manager.reset_session_abort(session_id)
            
            # 發送會話ID（如果是新創建的）
            if request.session_id != session_id:
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            
            # 發送開始信號
            yield f"data: {json.dumps({'type': 'start', 'message': '正在思考...'})}\n\n"
            
            # 檢查是否被中止
            if session_manager.is_session_aborted(session_id):
                yield f"data: {json.dumps({'type': 'aborted', 'message': '對話已中止'})}\n\n"
                return
            
            # 執行 RAG 查詢
            response = chat_engine.chat(request.message)
            
            # 檢查是否被中止
            if session_manager.is_session_aborted(session_id):
                yield f"data: {json.dumps({'type': 'aborted', 'message': '對話已中止'})}\n\n"
                return
            
            # 模擬串流效果（將回答分段發送）
            answer = response.response
            words = answer.split()
            
            current_text = ""
            for i, word in enumerate(words):
                # 每次檢查是否被中止
                if session_manager.is_session_aborted(session_id):
                    yield f"data: {json.dumps({'type': 'aborted', 'message': '對話已中止'})}\n\n"
                    return
                
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
        finally:
            # 清除處理狀態
            session_manager.set_processing_status(session_id, False)
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


@router.get("/sessions")
async def get_session_info():
    """獲取會話統計信息"""
    # 清理過期會話
    cleaned = session_manager.cleanup_expired_sessions()
    
    return {
        "active_sessions": session_manager.get_session_count(),
        "cleaned_sessions": cleaned
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """刪除指定會話"""
    deleted = session_manager.delete_session(session_id)
    return {
        "deleted": deleted,
        "message": "會話已刪除" if deleted else "會話不存在"
    }


@router.post("/abort/{session_id}")
async def abort_chat(session_id: str):
    """中止指定會話的當前對話"""
    # 檢查會話是否存在
    session = session_manager.get_session(session_id)
    if not session:
        return {
            "success": False,
            "message": "會話不存在"
        }
    
    # 檢查是否正在處理
    is_processing = session_manager.is_session_processing(session_id)
    if not is_processing:
        return {
            "success": False,
            "message": "當前沒有進行中的對話"
        }
    
    # 設置中止標誌
    aborted = session_manager.abort_session(session_id)
    return {
        "success": aborted,
        "message": "對話已中止" if aborted else "中止失敗",
        "session_id": session_id
    }


@router.post("/reset/{session_id}")
async def reset_session_state(session_id: str):
    """重置會話狀態，清除中止標誌但保留對話歷史"""
    # 檢查會話是否存在
    session = session_manager.get_session(session_id)
    if not session:
        return {
            "success": False,
            "message": "會話不存在"
        }
    
    # 重置中止狀態
    reset_success = session_manager.reset_session_abort(session_id)
    # 清除處理狀態
    session_manager.set_processing_status(session_id, False)
    
    return {
        "success": reset_success,
        "message": "會話狀態已重置" if reset_success else "重置失敗",
        "session_id": session_id
    }


@router.get("/status/{session_id}")
async def get_session_status(session_id: str):
    """獲取會話狀態"""
    session = session_manager.get_session(session_id)
    if not session:
        return {
            "exists": False,
            "message": "會話不存在"
        }
    
    return {
        "exists": True,
        "session_id": session_id,
        "is_processing": session_manager.is_session_processing(session_id),
        "is_aborted": session_manager.is_session_aborted(session_id),
        "created_at": session["created_at"],
        "last_access": session["last_access"]
    }


@router.get("/greeting/{session_id}")
async def get_intelligent_greeting(session_id: str):
    """獲取基於 RAG 的智能問候語"""
    # 檢查會話是否存在
    session = session_manager.get_session(session_id)
    if not session:
        return {
            "success": False,
            "message": "會話不存在"
        }
    
    # 獲取或創建聊天引擎
    chat_engine = session_manager.get_chat_engine(session_id)
    if not chat_engine:
        # 為這個會話創建新的聊天引擎
        memory = session_manager.get_or_create_memory(session_id)
        chat_engine = rag_service.create_chat_engine(memory)
        session_manager.set_chat_engine(session_id, chat_engine)
    
    try:
        # 使用 RAG 生成智能問候語
        greeting_prompt = "你好，我剛進入聊天室，請給我一個專業且友善的問候，並簡單說明你能幫助我什麼。"
        response = chat_engine.chat(greeting_prompt)
        
        return {
            "success": True,
            "greeting": response.response,
            "session_id": session_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"生成智能問候語時發生錯誤: {str(e)}",
            "fallback_greeting": generate_greeting()  # 提供備用問候語
        }