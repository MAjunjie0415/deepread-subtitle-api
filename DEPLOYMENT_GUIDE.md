# 🚀 部署指南 - 100% 成功保证

## 📋 第一步：推送到 GitHub（5分钟）

### 1. 在 GitHub 创建新仓库

1. 打开浏览器，访问：https://github.com/new
2. **Repository name**: `deepread-subtitle-api`
3. **Description**: `DeepRead 字幕提取服务`
4. 选择 **Public**（公开）
5. **不要**勾选任何选项（README、.gitignore、license）
6. 点击 **Create repository**

### 2. 推送代码

在终端执行（替换 YOUR_USERNAME 为你的 GitHub 用户名）：

```bash
cd /Users/mima0000/deepread-subtitle-api
git remote add origin https://github.com/YOUR_USERNAME/deepread-subtitle-api.git
git push -u origin main
```

✅ **验证**：刷新 GitHub 页面，应该能看到 5 个文件

---

## 📋 第二步：部署到 Zeabur（5分钟）

### 1. 注册并登录 Zeabur

1. 访问：https://zeabur.com
2. 点击右上角 **Sign in**
3. 选择 **Continue with GitHub**
4. 授权 Zeabur 访问你的 GitHub

### 2. 创建项目并部署

1. 进入 Zeabur 控制台后，点击 **Create Project**
2. **Project Name**: `deepread-subtitle`（随意）
3. 点击 **Create**

4. 在项目页面，点击 **Add Service**
5. 选择 **Git**
6. 找到并选择 `deepread-subtitle-api` 仓库
7. 点击 **Deploy**

### 3. 等待部署完成

- 屏幕会显示构建日志
- 看到 **"Building"** → **"Deploying"** → **"Running"**
- 大约 2-3 分钟

### 4. 获取 API 地址

1. 部署成功后，点击服务卡片
2. 点击 **Domains** 标签
3. 点击 **Generate Domain**
4. Zeabur 会自动生成一个域名，类似：
   ```
   https://deepread-subtitle-api-xxxxx.zeabur.app
   ```
5. **复制这个地址** - 后面要用

### 5. 测试 API 是否正常

打开终端，执行（替换为你的域名）：

```bash
curl https://your-domain.zeabur.app/
```

应该返回：
```json
{
  "status": "ok",
  "service": "DeepRead Subtitle API",
  "version": "1.0.0"
}
```

✅ **成功！** Zeabur 部署完成

---

## 📋 第三步：修改 Vercel 前端（5分钟）

### 1. 修改后端 API

打开 `/Users/mima0000/deepread-cc/src/app/api/pull/route.ts`

替换整个文件内容为：

```typescript
import { NextRequest, NextResponse } from 'next/server';

// Zeabur 字幕 API 地址（替换为你的实际地址）
const SUBTITLE_API = 'https://your-domain.zeabur.app/extract';

export async function POST(req: NextRequest) {
  try {
    const { url } = await req.json();

    if (!url) {
      return NextResponse.json(
        { success: false, error: 'URL is required' },
        { status: 400 }
      );
    }

    console.log(`🔄 转发字幕请求到 Zeabur: ${url}`);

    // 调用 Zeabur 字幕 API
    const response = await fetch(SUBTITLE_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
      signal: AbortSignal.timeout(60000) // 60秒超时
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Zeabur API 错误:', errorText);
      throw new Error(`Zeabur API failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✅ 成功获取 ${data.transcript?.length || 0} 段字幕`);

    return NextResponse.json(data);

  } catch (error: any) {
    console.error('❌ API 错误:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error.message || '服务器错误'
      },
      { status: 500 }
    );
  }
}
```

**⚠️ 重要**：把第 4 行的 `https://your-domain.zeabur.app/extract` 替换为你在 Zeabur 获取的实际域名！

### 2. 提交并推送

```bash
cd /Users/mima0000/deepread-cc
git add src/app/api/pull/route.ts
git commit -m "feat: 使用 Zeabur 字幕 API"
git push origin main
```

### 3. 等待 Vercel 部署

- Vercel 会自动检测到 GitHub 更新
- 自动开始构建和部署
- 大约 1-2 分钟

---

## 📋 第四步：测试完整流程（2分钟）

1. 访问：https://deepread-cc.vercel.app
2. 输入：`https://www.youtube.com/watch?v=7xTGNNLPyMI`
3. 点击 **"开始深度阅读"**
4. 等待 5-10 秒
5. 应该能看到完整字幕显示在右侧

✅ **大功告成！** 

---

## 🎯 成功标志

1. ✅ Zeabur 显示 "Running"
2. ✅ 测试 API 返回正常 JSON
3. ✅ Vercel 构建成功
4. ✅ 前端能正常显示字幕

---

## 🆘 如果失败怎么办

### Zeabur 构建失败
- 检查 Dockerfile、requirements.txt 是否正确
- 查看 Zeabur 控制台的构建日志

### Vercel 前端报错
- 检查 API 地址是否正确（末尾要加 `/extract`）
- 打开浏览器控制台（F12）查看错误信息

### 字幕获取失败
- 确认 Zeabur API 单独测试是否正常
- 查看 Vercel Function 日志

---

## 📞 需要帮助

把以下信息发给我：
1. Zeabur 的构建日志（如果构建失败）
2. Zeabur 生成的域名
3. Vercel Function 的错误日志
4. 浏览器控制台的错误信息

我会立即帮你解决！

