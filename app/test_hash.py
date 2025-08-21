from pathlib import Path
import hashlib


def file_hash(p: Path) -> str:
    h = hashlib.sha1()
    h.update(p.read_bytes())
    return h.hexdigest()

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data/policy.txt"

print("第一次 hash：", file_hash(DATA_FILE))

text = DATA_FILE.read_text(encoding="utf-8")
print("文件長度：", len(text))
print("是否包含'退貨'：", "退貨" in text)

print("第二次 hash：", file_hash(DATA_FILE))


# for file in DATA_DIR.rglob("*"):
#     if file.is_file():
#         print(f"{file.name}: {file_hash(file)}")
