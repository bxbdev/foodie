import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.prompts import PromptTemplate
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
    model=models[0],
    base_url=OLLAMA_URL,
    request_timeout=120.0,
)
Settings.embed_model = OllamaEmbedding(
    model_name="nomic-embed-text:latest",
    base_url=OLLAMA_URL
)

# vec = Settings.embed_model.get_text_embedding("hello world")
# print(len(vec), vec[:5])

# 設定目錄路徑
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
persist_dir = BASE_DIR / "storage"

qa_tmpl = PromptTemplate(
    "你是嚴謹的企業助理。只根據提供的內容回答"
    "\n\n[內容]\n{context_str}\n\n[問題]\n{query_str}"
    "\n\n若內容不足，請回答：不知道。"
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
            print("📁 第一次執行，建立新的 RAG 索引...")
        else:
            print("🔄 偵測到檔案變化，重建 RAG 索引...")
            # 清空舊的索引目錄
            if persist_dir.exists():
                import shutil
                shutil.rmtree(persist_dir)
        
        # 重新建立索引
        print("📖 正在讀取文件...")
        docs = SimpleDirectoryReader(
            str(DATA_DIR), 
            encoding="utf-8", 
            errors="ignore"
        ).load_data()
        
        print(f"✅ 成功載入 {len(docs)} 個文件")
        
        print("🔪 正在切分文本塊...")
        nodes = SentenceSplitter(
            chunk_size=800, 
            chunk_overlap=120
        ).get_nodes_from_documents(docs)
        
        print(f"✅ 生成 {len(nodes)} 個文本塊")
        
        print("🚀 正在建立向量索引...")
        index = VectorStoreIndex(nodes)
        
        print("💾 儲存索引到磁碟...")
        index.storage_context.persist(persist_dir=str(persist_dir))
        
        print("✅ 索引建立完成！")
        
    else:
        print("⚡ 沒有檔案變化，載入現有索引...")
        storage_ctx = StorageContext.from_defaults(persist_dir=str(persist_dir))
        index = load_index_from_storage(storage_ctx)
        print("✅ 索引載入完成！")
    
    return index

# 執行智能索引管理
index = create_or_load_index()

qe = index.as_query_engine(similarity_top_k=5, response_mode="compact", text_qa_template=qa_tmpl)
print(qe.query("退換貨可以幾天辦？").response)