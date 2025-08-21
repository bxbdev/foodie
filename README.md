## 生成 venv

```uv venv```

## 啟動 venv
```.venv\Scripts\activate```

## 取消啟動 venv

```deactivate```

## 優先安裝

```pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama fastapi uvicorn python-dotenv
```

## 快速生成 requirements.txt
```pip freeze > requirements.txt```

## 安裝 requirements.txt

### uv
```uv pip install -r requirements.txt```

### pip
```pip install -r requirements.txt```

## 執行
```uvicorn app.main:app --reload```


## 錯誤訊息
```json
{
  "detail": [
    {
      "type": "missing",        // 錯誤類型：缺少欄位
      "loc": [ "body", 2, "count" ], // 出錯位置：body 裡的第 2 筆資料的 count
      "msg": "Field required",  // 錯誤訊息：這個欄位是必填的
      "input": {
        "name": "kiwi",
        "price": 0.19
      }
    }
  ]
}
```

# 啟動指令

進到入 `foodie\app` 目錄

### 方式 1: 使用整合後的聊天應用

```uvicorn chat_app:app --reload --host 0.0.0.0 --port 8000```

### 方式 2: 使用模組化 API (如果想用 main.py)

```uvicorn main:app --reload --host 0.0.0.0 --port 8000```