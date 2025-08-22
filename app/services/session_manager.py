"""
RAG 會話管理器 - 處理多用戶上下文記憶
"""
import uuid
import time
from typing import Dict, Optional, Any
from threading import Lock
from llama_index.core.memory import Memory


class SessionManager:
    """管理多用戶的 RAG 聊天會話和記憶"""
    
    def __init__(self, session_timeout: int = 3600):  # 1小時超時
        self.sessions: Dict[str, dict] = {}
        self.lock = Lock()
        self.session_timeout = session_timeout
    
    def create_session(self) -> str:
        """創建新的會話ID"""
        session_id = str(uuid.uuid4())
        
        with self.lock:
            self.sessions[session_id] = {
                'memory': Memory.from_defaults(token_limit=3000),
                'chat_engine': None,  # 將在需要時初始化
                'created_at': time.time(),
                'last_access': time.time(),
                'is_aborted': False,  # 中止狀態
                'is_processing': False  # 處理狀態
            }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """獲取會話數據"""
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            session['last_access'] = time.time()
            return session
    
    def get_or_create_memory(self, session_id: str) -> Memory:
        """獲取或創建會話記憶"""
        session = self.get_session(session_id)
        if session is None:
            # 自動創建新會話
            new_session_id = self.create_session()
            session = self.get_session(new_session_id)
        
        return session['memory']
    
    def set_chat_engine(self, session_id: str, chat_engine: Any):
        """設置會話的聊天引擎"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['chat_engine'] = chat_engine
    
    def get_chat_engine(self, session_id: str) -> Optional[Any]:
        """獲取會話的聊天引擎"""
        session = self.get_session(session_id)
        return session['chat_engine'] if session else None
    
    def cleanup_expired_sessions(self):
        """清理過期的會話"""
        current_time = time.time()
        expired_sessions = []
        
        with self.lock:
            for session_id, session_data in self.sessions.items():
                if current_time - session_data['last_access'] > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
        
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """獲取活躍會話數量"""
        with self.lock:
            return len(self.sessions)
    
    def delete_session(self, session_id: str) -> bool:
        """刪除指定會話"""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def abort_session(self, session_id: str) -> bool:
        """中止指定會話的當前對話"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['is_aborted'] = True
                return True
            return False
    
    def is_session_aborted(self, session_id: str) -> bool:
        """檢查會話是否被中止"""
        with self.lock:
            if session_id in self.sessions:
                return self.sessions[session_id]['is_aborted']
            return False
    
    def reset_session_abort(self, session_id: str) -> bool:
        """重置會話的中止狀態"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['is_aborted'] = False
                return True
            return False
    
    def set_processing_status(self, session_id: str, is_processing: bool) -> bool:
        """設置會話的處理狀態"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['is_processing'] = is_processing
                return True
            return False
    
    def is_session_processing(self, session_id: str) -> bool:
        """檢查會話是否正在處理"""
        with self.lock:
            if session_id in self.sessions:
                return self.sessions[session_id]['is_processing']
            return False


# 全域會話管理器實例
session_manager = SessionManager()