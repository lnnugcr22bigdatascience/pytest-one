# 图片压缩工具

一个基于 Flask 的在线图片压缩工具，支持多种图片格式的批量压缩、实时预览和打包下载。所有处理均在内存中完成，无需存储文件。

## ✨ 功能特性

- 支持格式：JPG、PNG、WebP、BMP、GIF
- 单张/批量压缩（最多 20 张）
- 可调节压缩质量（10% ~ 100%），内置高/中/低预设
- 保留 PNG/GIF 透明通道，压缩为 JPEG 时自动填充白色背景
- 压缩前后尺寸、大小、格式对比展示
- 单张下载或打包为 ZIP 批量下载
- 完全本地处理，不上传任何文件到服务器

## 🛠 技术栈

- 后端：Flask + Pillow
- 前端：原生 HTML/CSS/JS（无第三方依赖）
- 文件处理：内存 BytesIO，临时存储使用内存字典

## 📦 安装与运行

### 1. 克隆项目

```bash
git clone <repo-url>
cd image-compressor
```

### 2. 安装依赖

建议使用虚拟环境（如 `venv` 或 `conda`）：

```bash
pip install flask Pillow
```

### 3. 启动服务

```bash
python app.py
```

服务将在 `http://0.0.0.0:5000` 启动。

> 开发模式已开启 `debug=True`，生产环境请关闭。

## 📖 使用方法

1. 打开浏览器访问 `http://localhost:5000`
2. 拖放或点击选择图片（可多选）
3. 调整压缩质量滑块或点击预设按钮
4. 点击“开始压缩”按钮
5. 查看压缩结果预览和对比
6. 单张点击“下载”，或点击“下载全部 (ZIP)”批量导出

## 🔌 API 接口

### `POST /api/compress-batch`

批量压缩图片

**请求参数** (multipart/form-data)

| 参数 | 类型 | 描述 |
|------|------|------|
| `files` | file[] | 图片文件列表（最多20个） |
| `quality` | int | 压缩质量 10-100，默认70 |

**响应示例**

```json
{
  "batch_id": "abc123",
  "results": [
    {
      "download_id": "xyz789",
      "original_name": "photo.jpg",
      "original_size": 102400,
      "compressed_size": 51200,
      "original_width": 1920,
      "original_height": 1080,
      "compression_ratio": 50.0,
      "output_format": "JPEG",
      ...
    }
  ],
  "total_original_size": 102400,
  "total_compressed_size": 51200,
  "total_compression_ratio": 50.0
}
```

### `GET /api/download/<download_id>`

下载单个压缩后的图片

### `GET /api/download-batch/<batch_id>`

下载整个批次的 ZIP 压缩包

> 文件在内存中暂存，下载后立即清除。批处理结果需及时下载。

## ⚠️ 注意事项

- 单个文件最大 **20MB**，总请求体最大 **50MB**
- 多次上传会累加文件列表，最多可同时选择 20 张
- PNG 透明图压缩为 JPEG 时会将透明区域变为白色背景
- 服务重启后临时下载链接将失效（内存存储）
- 生产部署建议使用 `waitress` 或 `gunicorn`，并增加文件清理机制

## 📄 开源协议

MIT
