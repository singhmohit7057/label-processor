from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import io, zipfile, base64

from processor import pdf_to_images, process_page

app = FastAPI()

# ✅ FIXED CORS (production safe)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# PROCESS
# =========================
@app.post("/process")
async def process(
    file: UploadFile = File(...),
    size: str = Form(...),
    output: str = Form(...),
    zip_enabled: str = Form("1")
):
    try:
        pdf_bytes = await file.read()
        pages = pdf_to_images(pdf_bytes)

        if zip_enabled == "1":
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for i, page in enumerate(pages, 1):
                    s, inv = process_page(page, size)

                    if output == "separate":
                        sb, ib = io.BytesIO(), io.BytesIO()
                        s.save(sb, "PDF")
                        inv.save(ib, "PDF")

                        zipf.writestr(f"s_{i}.pdf", sb.getvalue())
                        zipf.writestr(f"i_{i}.pdf", ib.getvalue())

                    else:
                        cb = io.BytesIO()
                        s.save(cb, "PDF", save_all=True, append_images=[inv])
                        zipf.writestr(f"c_{i}.pdf", cb.getvalue())

            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=output.zip"}
            )

        # single PDF
        s, inv = process_page(pages[0], size)

        buffer = io.BytesIO()
        s.save(buffer, "PDF", save_all=True, append_images=[inv])
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=output.pdf"}
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =========================
# PREVIEW
# =========================
@app.post("/preview")
async def preview(
    file: UploadFile = File(...),
    size: str = Form(...),
    output: str = Form(...)
):
    try:
        pdf_bytes = await file.read()
        pages = pdf_to_images(pdf_bytes)

        images = []

        for page in pages[:1]:
            shipping, invoice = process_page(page, size)

            import base64
            buf1, buf2 = io.BytesIO(), io.BytesIO()

            shipping.save(buf1, format="PNG")
            invoice.save(buf2, format="PNG")

            images.append(base64.b64encode(buf1.getvalue()).decode())
            images.append(base64.b64encode(buf2.getvalue()).decode())

        return {"images": images}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/")
def home():
    return {"ok": True}