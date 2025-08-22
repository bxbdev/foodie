"""
RAG 服務 - 整合現有的 RAG 聊天引擎
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.prompts import PromptTemplate
from llama_index.core.memory import Memory
from utils.file_monitor import FileMonitor


class RAGService:
    """RAG 服務單例類"""
    
    def __init__(self):
        self.index = None
        self._initialize()
    
    def _initialize(self):
        """初始化 RAG 服務"""
        # 載入環境變數
        load_dotenv()
        OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        # 模型設定
        models = [
            "gemma3:27b",
            "codellama:34b", 
            "llama3.2-vision:11b",
        ]
        
        # 設置 LLM 和 Embedding
        Settings.llm = Ollama(
            model=models[0],
            base_url=OLLAMA_URL,
            request_timeout=120.0,
        )
        Settings.embed_model = OllamaEmbedding(
            model_name="nomic-embed-text:latest",
            base_url=OLLAMA_URL
        )
        
        # 設定目錄路徑
        BASE_DIR = Path(__file__).resolve().parent.parent
        DATA_DIR = BASE_DIR / "data"
        persist_dir = BASE_DIR / "storage"
        
        # 創建或載入索引
        self.index = self._create_or_load_index(DATA_DIR, persist_dir)
    
    def _create_or_load_index(self, data_dir, persist_dir):
        """創建或載入索引（複製自 rag_ollama_fixed.py）"""
        from llama_index.core import SimpleDirectoryReader
        from llama_index.core.node_parser import SentenceSplitter
        
        print("=== RAG 服務初始化 ===")
        
        # 建立檔案監控器
        monitor = FileMonitor(data_dir)
        
        # 檢查是否存在舊的索引
        index_exists = persist_dir.exists() and any(persist_dir.iterdir())
        
        # 檢查檔案是否有變化
        has_changes, changed_files = monitor.has_changes()
        
        # 決定是否需要重建索引
        need_rebuild = not index_exists or has_changes
        
        if need_rebuild:
            if not index_exists:
                print("[建立] 第一次執行，建立新的 RAG 索引...")
            else:
                print("[重建] 偵測到檔案變化，重建 RAG 索引...")
                print("變化的檔案:")
                for change in changed_files:
                    print(f"  - {change}")
                
                # 清空舊的索引目錄
                if persist_dir.exists():
                    import shutil
                    shutil.rmtree(persist_dir)
            
            # 重新建立索引
            print("[載入] 正在讀取文件...")
            docs = SimpleDirectoryReader(
                str(data_dir), 
                encoding="utf-8", 
                errors="ignore"
            ).load_data()
            
            print(f"[完成] 成功載入 {len(docs)} 個文件")
            
            print("[處理] 正在切分文本塊...")
            nodes = SentenceSplitter(
                chunk_size=800, 
                chunk_overlap=120
            ).get_nodes_from_documents(docs)
            
            print(f"[完成] 生成 {len(nodes)} 個文本塊")
            
            print("[索引] 正在建立向量索引...")
            index = VectorStoreIndex(nodes)
            
            print("[儲存] 儲存索引到磁盤...")
            index.storage_context.persist(persist_dir=str(persist_dir))
            
            print("[完成] 索引建立完成！")
            
        else:
            print("[載入] 沒有檔案變化，載入現有索引...")
            storage_ctx = StorageContext.from_defaults(persist_dir=str(persist_dir))
            index = load_index_from_storage(storage_ctx)
            print("[完成] 索引載入完成！")
        
        return index
    
    def create_chat_engine(self, memory: Memory):
        """為指定的記憶創建聊天引擎"""
        qa_tmpl = PromptTemplate(
            "你是專業的客服助理。根據對話歷史和退貨政策來回答客戶問題。"
            "\n\n[退貨政策內容]\n{context_str}\n\n[客戶問題]\n{query_str}"
            "\n\n重要指引："
            "\n1. 仔細讀取對話歷史，準確記錄客戶已提供的資訊"
            "\n2. 絕對不要重複已說過的內容或要求已提供的資訊"
            "\n3. 如果客戶表示感謝、滿意或「沒問題了」，請簡潔回應：「好的，感謝您的配合。如有其他問題歡迎隨時聯繫我們！」"
            "\n4. 每次只回應一個段落，不要重複同樣的內容"
            "\n5. 準確引用客戶提供的訂單編號、姓名等資訊"
            "\n6. 保持專業且簡潔的語調"
        )
        
        return self.index.as_chat_engine(
            chat_mode="context",  # 改用 context 模式，更好處理對話歷史
            memory=memory,
            similarity_top_k=2,  # 進一步減少檢索數量
            text_qa_template=qa_tmpl,
            verbose=False,  # 關閉詳細輸出
            system_prompt="你是專業的客服助理，請根據對話歷史提供簡潔準確的回應，避免重複內容。"
        )
    
    def get_index(self):
        """獲取索引實例"""
        return self.index


# 全域 RAG 服務實例
rag_service = RAGService()