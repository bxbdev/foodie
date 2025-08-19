## 生成 venv

```uv venv```

## 啟動 venv
```.venv\Scripts\activate```

## 取消啟動 venv

```deactivate```

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

