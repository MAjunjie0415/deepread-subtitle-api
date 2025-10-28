# DeepRead Subtitle API

YouTube 字幕提取服务 - 部署在 Zeabur

## 功能

- ✅ 自动提取 YouTube 字幕
- ✅ 支持多种语言（英语、中文）
- ✅ 自动翻页获取完整字幕
- ✅ 标准化格式输出

## API 端点

### GET /
健康检查

### POST /extract
提取字幕

**请求体：**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**响应：**
```json
{
  "success": true,
  "video_id": "VIDEO_ID",
  "transcript": [...],
  "meta": {
    "segment_count": 1387,
    "word_count": 22800,
    "duration_seconds": 3602,
    "duration_formatted": "60:02"
  }
}
```

## 本地测试

```bash
pip install -r requirements.txt
python main.py
```

访问 http://localhost:8000

## 部署到 Zeabur

1. 推送到 GitHub
2. 在 Zeabur 选择仓库
3. 自动部署

就这么简单！

