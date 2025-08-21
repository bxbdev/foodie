import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.prompts import PromptTemplate
from llama_index.core.memory import ChatMemoryBuffer
from file_monitor import FileMonitor  # 匯入我們的檔案監控系統

# 載入環境變數
load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")  # 預設值作為 fallback 

models = [
    "gemma3:27b",
    "codellama:34b",
    "llama3.2-vision:11b",
]

Settings.llm = Ollama(
    model=models[2],
    base_url=OLLAMA_URL,
    request_timeout=120.0,
)
Settings.embed_model = OllamaEmbedding(
    model_name="nomic-embed-text:latest",
    base_url=OLLAMA_URL
)


# 設定目錄路徑
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
persist_dir = BASE_DIR / "storage"

memory = ChatMemoryBuffer.from_defaults(token_limit=3000)
qa_tmpl = PromptTemplate(
    "你是專業的客服助理。根據提供的退貨政策內容回答問題，需要合理推理相關條款。"
    "\n\n[退貨政策內容]\n{context_str}\n\n[客戶問題]\n{query_str}"
    "\n\n回答指引："
    "\n- 仔細分析所有相關條款"
    "\n- 提供明確的答案和依據"
    "\n- 如果有灰色地帶，建議聯絡客服"
    "\n- 只有在政策完全沒有涉及時才回答「不知道」"
)

def create_or_load_index():
    """
    智能索引管理函數：根據檔案變化決定是建立新索引還是載入現有索引
    """
    print("=== 智能 RAG 索引管理系統 ===")
    
    # 1. 建立檔案監控器
    monitor = FileMonitor(DATA_DIR)
    
    # 2. 檢查是否存在舊的索引
    index_exists = persist_dir.exists() and any(persist_dir.iterdir())
    
    # 3. 檢查檔案是否有變化
    has_changes, changed_files = monitor.has_changes()
    
    # 4. 決定是否需要重建索引
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
            str(DATA_DIR), 
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

def main():
    """主程式函數"""
    # 執行智能索引管理
    index = create_or_load_index()
    
    # 建立帶記憶功能的聊天引擎
    print("\n[查詢] 準備聊天引擎...")
    qe = index.as_chat_engine(
        chat_mode="condense_question",
        memory=memory,
        similarity_top_k=5, 
        text_qa_template=qa_tmpl,
        verbose=True
    )
    
    # 開始互動式查詢
    print("\n[互動] RAG 查詢系統已準備完成！")
    print("輸入你的問題，輸入 'quit' 或 'exit' 退出")
    print("-" * 50)
    
    while True:
        try:
            # 取得用戶輸入
            question = input("\n問題> ").strip()
            
            # 檢查退出條件
            if question.lower() in ['quit', 'exit', '退出', 'q']:
                print("感謝使用 RAG 查詢系統！")
                break
            
            # 檢查空輸入
            if not question:
                print("請輸入一個問題...")
                continue
            
            # 執行聊天查詢
            print(f"\n[查詢] 正在搜尋: {question}")
            response = qe.chat(question)
            print(f"[答案] {response.response}")
            
        except KeyboardInterrupt:
            print("\n\n系統中斷，再見！")
            break
        except Exception as e:
            print(f"發生錯誤: {e}")
            print("請重新輸入問題...")
    
    print("\n=== 系統運行完成 ===")

if __name__ == "__main__":
    main()