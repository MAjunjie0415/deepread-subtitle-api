from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = Flask(__name__)

def get_video_id(url):
    """从 YouTube URL 提取视频 ID"""
    m = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None

@app.route("/", methods=["GET"])
def home():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": "DeepRead Subtitle API",
        "version": "1.0.0"
    })

@app.route("/extract", methods=["POST"])
def extract():
    """提取 YouTube 字幕 - 支持完整翻页"""
    url = request.json.get("url", "")
    vid = get_video_id(url)
    
    if not vid:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        print(f"\n{'='*60}")
        print(f"🎯 开始提取字幕")
        print(f"📹 视频 ID: {vid}")
        print(f"{'='*60}")
        
        # 获取完整字幕（自动翻页）
        segments = []
        page = 0
        
        # 尝试多种语言
        languages_to_try = [['en'], ['en-US'], ['a.en'], ['zh-CN', 'zh-Hans']]
        
        last_error = None
        for langs in languages_to_try:
            try:
                print(f"\n🔄 尝试语言: {langs}")
                # 获取可用的字幕列表
                transcript_list = YouTubeTranscriptApi.list_transcripts(vid)
                print(f"📋 可用字幕: {[t.language_code for t in transcript_list]}")
                
                transcript = YouTubeTranscriptApi.get_transcript(vid, languages=langs)
                segments = transcript
                print(f"✅ 成功获取 {len(segments)} 段字幕")
                break
            except Exception as e:
                print(f"❌ {langs} 失败: {str(e)}")
                last_error = e
                continue
        
        if not segments:
            error_msg = f"No transcript available. Last error: {str(last_error)}" if last_error else "No transcript available"
            print(f"\n❌ 最终失败: {error_msg}")
            return jsonify({"error": error_msg}), 404
        
        # 格式化输出
        full_text = " ".join([s["text"] for s in segments])
        
        # 格式化为标准格式
        formatted_segments = []
        for idx, seg in enumerate(segments):
            formatted_segments.append({
                "segment_id": f"seg_{str(idx).zfill(4)}",
                "start": seg["start"],
                "duration": seg["duration"],
                "end": seg["start"] + seg["duration"],
                "timestamp": format_timestamp(seg["start"]),
                "text": seg["text"]
            })
        
        # 统计信息
        total_duration = segments[-1]["start"] + segments[-1]["duration"] if segments else 0
        word_count = len(full_text.split())
        
        print(f"\n{'='*60}")
        print(f"✅ 提取成功！")
        print(f"📝 总段数: {len(formatted_segments)}")
        print(f"💬 总字数: {word_count}")
        print(f"⏱️  时长: {format_timestamp(total_duration)}")
        print(f"{'='*60}\n")
        
        return jsonify({
            "success": True,
            "video_id": vid,
            "transcript": formatted_segments,
            "meta": {
                "segment_count": len(formatted_segments),
                "word_count": word_count,
                "duration_seconds": total_duration,
                "duration_formatted": format_timestamp(total_duration),
                "source": "youtube_transcript_api"
            }
        })
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}\n")
        return jsonify({"error": str(e)}), 500

def format_timestamp(seconds):
    """格式化时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{str(minutes).zfill(2)}:{str(secs).zfill(2)}"
    return f"{minutes}:{str(secs).zfill(2)}"

if __name__ == "__main__":
    # 监听 0.0.0.0 方便容器访问
    # Zeabur 使用 8080 端口
    port = 8080
    print("\n🚀 DeepRead Subtitle API 启动中...")
    print(f"📡 监听端口: {port}")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)

