import io
import uuid
import zipfile
from flask import Flask, request, jsonify, send_file
from PIL import Image

app = Flask(__name__, static_folder="static", static_url_path="")

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB total

temp_files: dict[str, dict] = {}


@app.route("/")
def index():
    return app.send_static_file("index.html")


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "gif"}

EXT_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "gif": "image/gif",
}


def _compress_image(file_data: bytes, filename: str, quality: int) -> dict:
    quality = max(10, min(100, quality))

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {ext}")

    original_size = len(file_data)
    img = Image.open(io.BytesIO(file_data))
    orig_w, orig_h = img.size
    orig_fmt = img.format or ext.upper()

    # Determine output format: keep PNG/GIF if transparency, else JPEG for size
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in (img.info or {})
    )
    if orig_fmt in ("PNG", "WEBP") and not has_alpha:
        out_fmt = "JPEG"
    elif orig_fmt == "GIF":
        out_fmt = "GIF"
    else:
        out_fmt = orig_fmt if orig_fmt in ("PNG", "WEBP") else "JPEG"

    # Convert alpha to white background when saving as JPEG
    if out_fmt == "JPEG" and has_alpha:
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1])
        img = bg

    out_buf = io.BytesIO()
    save_args = {"format": out_fmt, "optimize": True}
    if out_fmt == "JPEG":
        save_args["quality"] = quality
    elif out_fmt == "WEBP":
        save_args["quality"] = quality

    img.save(out_buf, **save_args)
    compressed_size = out_buf.getbuffer().nbytes

    download_id = str(uuid.uuid4())[:12]
    ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif", "BMP": "bmp"}
    out_ext = ext_map.get(out_fmt, "jpg")
    out_filename = f"{filename.rsplit('.', 1)[0]}_compressed.{out_ext}"

    temp_files[download_id] = {
        "data": out_buf.getvalue(),
        "filename": out_filename,
        "mimetype": EXT_TO_MIME[out_ext],
    }

    ratio = round((1 - compressed_size / original_size) * 100, 1) if original_size > 0 else 0

    return {
        "download_id": download_id,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "original_width": orig_w,
        "original_height": orig_h,
        "compressed_width": orig_w,
        "compressed_height": orig_h,
        "original_format": orig_fmt,
        "output_format": out_fmt,
        "compression_ratio": ratio,
        "original_name": filename,
    }


@app.route("/api/compress", methods=["POST"])
def compress():
    if "file" not in request.files:
        return jsonify({"error": "请选择文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "请选择文件"}), 400

    quality = int(request.form.get("quality", 70))

    try:
        original_data = file.read()
        if len(original_data) > 20 * 1024 * 1024:
            return jsonify({"error": "文件不能超过 20MB"}), 400
        result = _compress_image(original_data, file.filename, quality)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"压缩失败: {str(e)}"}), 500


@app.route("/api/compress-batch", methods=["POST"])
def compress_batch():
    files = request.files.getlist("files")
    if not files or all(not f.filename for f in files):
        return jsonify({"error": "请选择文件"}), 400

    quality = int(request.form.get("quality", 70))
    max_files = 20
    if len(files) > max_files:
        return jsonify({"error": f"单次最多处理 {max_files} 个文件"}), 400

    results = []
    batch_ids = []
    for f in files:
        if not f.filename:
            continue
        try:
            original_data = f.read()
            if len(original_data) > 20 * 1024 * 1024:
                results.append({"original_name": f.filename, "error": "文件超过 20MB"})
                continue
            result = _compress_image(original_data, f.filename, quality)
            results.append(result)
            batch_ids.append(result["download_id"])
        except ValueError as e:
            results.append({"original_name": f.filename, "error": str(e)})
        except Exception:
            results.append({"original_name": f.filename, "error": "压缩失败"})

    batch_id = str(uuid.uuid4())[:12]
    temp_files[f"batch_{batch_id}"] = {
        "type": "batch",
        "ids": batch_ids,
    }

    total_orig = sum(r.get("original_size", 0) for r in results)
    total_comp = sum(r.get("compressed_size", 0) for r in results)
    total_ratio = (
        round((1 - total_comp / total_orig) * 100, 1) if total_orig > 0 else 0
    )

    return jsonify({
        "batch_id": batch_id,
        "results": results,
        "total_original_size": total_orig,
        "total_compressed_size": total_comp,
        "total_compression_ratio": total_ratio,
    })


@app.route("/api/download/<download_id>")
def download_file(download_id):
    info = temp_files.pop(download_id, None)
    if not info:
        return jsonify({"error": "文件不存在或已过期"}), 404
    return send_file(
        io.BytesIO(info["data"]),
        mimetype=info["mimetype"],
        as_attachment=True,
        download_name=info["filename"],
    )


@app.route("/api/download-batch/<batch_id>")
def download_batch(batch_id):
    info = temp_files.pop(f"batch_{batch_id}", None)
    if not info:
        return jsonify({"error": "批次不存在或已过期"}), 404

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for download_id in info["ids"]:
            file_info = temp_files.pop(download_id, None)
            if file_info:
                zf.writestr(file_info["filename"], file_info["data"])

    zip_buf.seek(0)
    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="compressed_images.zip",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
