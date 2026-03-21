from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io, zipfile, base64
import fitz

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DPI = 300


def pdf_to_images(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)

    return pages


def process_images(pages, size):
    SHIPPING_SIZE = (3 * DPI, 5 * DPI) if size == "3x5" else (4 * DPI, 6 * DPI)
    INVOICE_SIZE = (4 * DPI, 6 * DPI)

    results = []

    for img in pages:
        w, h = img.size

        shipping = img.crop((0, int(h * 0.02), w, int(h * 0.462)))
        shipping = shipping.resize(SHIPPING_SIZE).convert("RGB")

        rotated = img.rotate(90, expand=True)
        rw, rh = rotated.size

        invoice = rotated.crop((
            int(rw * 0.385),
            int(rh * 0.07),
            int(rw * 0.95),
            int(rh * 0.92)
        ))
        invoice = invoice.resize(INVOICE_SIZE).convert("RGB")

        results.append((shipping, invoice))

    return results


# =========================
# 🚀 PROCESS
# =========================
@app.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    size: str = Form(...),
    output: str = Form(...),
    zip_enabled: str = Form("1")
):
    pdf_bytes = await file.read()
    pages = pdf_to_images(pdf_bytes)
    processed = process_images(pages, size)

    zip_flag = zip_enabled == "1"

    if zip_flag:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for i, (shipping, invoice) in enumerate(processed, 1):

                if output == "separate":
                    s_buf, i_buf = io.BytesIO(), io.BytesIO()
                    shipping.save(s_buf, "PDF")
                    invoice.save(i_buf, "PDF")

                    zipf.writestr(f"page{i}_shipping.pdf", s_buf.getvalue())
                    zipf.writestr(f"page{i}_invoice.pdf", i_buf.getvalue())

                else:
                    c_buf = io.BytesIO()
                    shipping.save(
                        c_buf,
                        "PDF",
                        save_all=True,
                        append_images=[invoice]
                    )
                    zipf.writestr(f"page{i}_combined.pdf", c_buf.getvalue())

        zip_buffer.seek(0)  # 🔥 FIX

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=output.zip"}
        )

    else:
        shipping, invoice = processed[0]

        buffer = io.BytesIO()
        shipping.save(buffer, "PDF", save_all=True, append_images=[invoice])

        buffer.seek(0)  # 🔥 FIX

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=output.pdf"}
        )


# =========================
# 👀 PREVIEW
# =========================
@app.post("/preview")
async def preview_pdf(
    file: UploadFile = File(...),
    size: str = Form(...),
    output: str = Form(...)
):
    pdf_bytes = await file.read()
    pages = pdf_to_images(pdf_bytes)
    processed = process_images(pages, size)

    previews = []

    for shipping, invoice in processed[:2]:
        buf = io.BytesIO()

        if output == "combined":
            shipping.save(buf, "PNG")
        else:
            shipping.save(buf, "PNG")

        previews.append(base64.b64encode(buf.getvalue()).decode())

    return JSONResponse({"images": previews})


@app.get("/")
def home():
    return {"status": "API running 🚀"}