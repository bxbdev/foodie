"""
檔案變化監控系統
用於偵測資料檔案是否有變化，以決定是否需要重建 RAG 索引
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List


class FileMonitor:
    """檔案監控類別，負責追蹤檔案變化"""
    
    def __init__(self, data_dir: Path, cache_file: str = "file_hashes.json"):
        """
        初始化檔案監控器
        
        Args:
            data_dir: 要監控的資料目錄
            cache_file: 儲存檔案 hash 的快取檔案名稱
        """
        self.data_dir = Path(data_dir)
        self.cache_file = self.data_dir.parent / cache_file
        self.supported_extensions = {'.txt', '.pdf', '.docx', '.md', '.json', '.xlsx', '.xls', '.csv'}
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        計算單一檔案的 SHA1 hash 值
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            檔案的 hash 值字串
        """
        hash_obj = hashlib.sha1()
        
        try:
            # 以二進位模式讀取檔案，避免編碼問題
            with open(file_path, 'rb') as file:
                # 分塊讀取大檔案，避免記憶體不足
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except (IOError, OSError) as e:
            print(f"無法讀取檔案 {file_path}: {e}")
            return ""
    
    def scan_directory(self) -> Dict[str, str]:
        """
        掃描資料目錄，取得所有支援檔案的 hash 值
        
        Returns:
            檔案路徑對應 hash 值的字典
        """
        current_hashes = {}
        
        # 使用 rglob 遞迴搜尋所有檔案
        for file_path in self.data_dir.rglob("*"):
            # 只處理檔案（非目錄）且副檔名在支援清單中
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                # 使用相對路徑作為 key，方便跨平台使用
                relative_path = str(file_path.relative_to(self.data_dir))
                file_hash = self.calculate_file_hash(file_path)
                
                if file_hash:  # 只有成功計算 hash 的檔案才加入
                    current_hashes[relative_path] = file_hash
                    print(f"掃描檔案: {relative_path} -> {file_hash[:10]}...")
        
        return current_hashes
    
    def load_cached_hashes(self) -> Dict[str, str]:
        """
        從快取檔案載入之前記錄的檔案 hash 值
        
        Returns:
            之前記錄的檔案 hash 字典，如果沒有快取則回傳空字典
        """
        if not self.cache_file.exists():
            print("沒有找到快取檔案，這是第一次執行")
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                print(f"載入快取檔案: {len(cached_data)} 個檔案記錄")
                return cached_data
        except (json.JSONDecodeError, IOError) as e:
            print(f"載入快取檔案失敗: {e}")
            return {}
    
    def save_hashes(self, hashes: Dict[str, str]) -> None:
        """
        將檔案 hash 值儲存到快取檔案
        
        Args:
            hashes: 要儲存的檔案 hash 字典
        """
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(hashes, f, indent=2, ensure_ascii=False)
            print(f"已儲存 {len(hashes)} 個檔案的 hash 到快取")
        except IOError as e:
            print(f"儲存快取檔案失敗: {e}")
    
    def has_changes(self) -> tuple[bool, List[str]]:
        """
        檢查檔案是否有變化
        
        Returns:
            (是否有變化, 變化的檔案清單)
        """
        print("正在檢查檔案變化...")
        
        # 取得目前檔案的 hash 值
        current_hashes = self.scan_directory()
        
        # 載入快取的 hash 值
        cached_hashes = self.load_cached_hashes()
        
        # 比較找出變化的檔案
        changed_files = []
        
        # 檢查新增或修改的檔案
        for file_path, current_hash in current_hashes.items():
            if file_path not in cached_hashes:
                changed_files.append(f"新增: {file_path}")
            elif cached_hashes[file_path] != current_hash:
                changed_files.append(f"修改: {file_path}")
        
        # 檢查刪除的檔案
        for file_path in cached_hashes:
            if file_path not in current_hashes:
                changed_files.append(f"刪除: {file_path}")
        
        # 更新快取
        if changed_files:
            self.save_hashes(current_hashes)
            print(f"偵測到 {len(changed_files)} 個檔案變化")
            for change in changed_files:
                print(f"  - {change}")
        else:
            print("沒有檔案變化")
        
        return len(changed_files) > 0, changed_files


# 測試用的主程式
if __name__ == "__main__":
    # 建立檔案監控器
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    
    monitor = FileMonitor(data_dir)
    
    # 檢查變化
    has_changes, changes = monitor.has_changes()
    
    if has_changes:
        print("\\n需要重建 RAG 索引！")
    else:
        print("\\n檔案沒有變化，可以使用現有索引")