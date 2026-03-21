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


# =========================
# PDF → IMAGES (SAFE)
# =========================
def pdf_to_images(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for page in doc:
        pix = page.get_pixmap()  # 🔥 SAFE (no matrix crash)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)

    if not pages:
        raise Exception("No pages extracted from PDF")

    return pages


# =========================
# PROCESS PAGE
# =========================
def process_page(img, size):
    SHIPPING_SIZE = (900, 1500) if size == "3x5" else (1200, 1800)
    INVOICE_SIZE = (1200, 1800)

    w, h = img.size

    # SHIPPING
    shipping = img.crop((0, int(h * 0.02), w, int(h * 0.462)))
    shipping = shipping.resize(SHIPPING_SIZE).convert("RGB")

    # INVOICE
    rotated = img.rotate(90, expand=True)
    rw, rh = rotated.size

    invoice = rotated.crop((
        int(rw * 0.385),
        int(rh * 0.07),
        int(rw * 0.95),
        int(rh * 0.92)
    ))
    invoice = invoice.resize(INVOICE_SIZE).convert("RGB")

    return shipping, invoice


# =========================
# PROCESS ENDPOINT
# =========================
@app.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    size: str = Form(...),
    output: str = Form(...),
    zip_enabled: str = Form("1")
):
    try:
        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise Exception("Empty file received")

        pages = pdf_to_images(pdf_bytes)
        zip_flag = zip_enabled == "1"

        # ================= ZIP =================
        if zip_flag:
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for i, page in enumerate(pages, 1):
                    shipping, invoice = process_page(page, size)

                    if output == "separate":
                        s_buf, i_buf = io.BytesIO(), io.BytesIO()
                        shipping.save(s_buf, format="PDF")
                        invoice.save(i_buf, format="PDF")

                        zipf.writestr(f"page{i}_shipping.pdf", s_buf.getvalue())
                        zipf.writestr(f"page{i}_invoice.pdf", i_buf.getvalue())

                    else:
                        c_buf = io.BytesIO()
                        shipping.save(
                            c_buf,
                            format="PDF",
                            save_all=True,
                            append_images=[invoice]
                        )
                        zipf.writestr(f"page{i}_combined.pdf", c_buf.getvalue())

            zip_buffer.seek(0)

            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=output.zip"}
            )

        # ================= PDF =================
        else:
            shipping, invoice = process_page(pages[0], size)

            buffer = io.BytesIO()

            shipping.save(
                buffer,
                format="PDF",
                save_all=True,
                append_images=[invoice]
            )

            buffer.seek(0)

            if buffer.getbuffer().nbytes < 100:
                raise Exception("Generated PDF is invalid")

            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=output.pdf"}
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =========================
# PREVIEW ENDPOINT
# =========================
@app.post("/preview")
async def preview_pdf(
    file: UploadFile = File(...),
    size: str = Form(...),
    output: str = Form(...)
):
    try:
        pdf_bytes = await file.read()
        pages = pdf_to_images(pdf_bytes)

        previews = []

        for page in pages[:2]:
            shipping, invoice = process_page(page, size)

            if output == "combined":
                combined = Image.new(
                    "RGB",
                    (shipping.width, shipping.height + invoice.height),
                    "white"
                )
                combined.paste(shipping, (0, 0))
                combined.paste(invoice, (0, shipping.height))

                buf = io.BytesIO()
                combined.save(buf, format="PNG")

            else:
                buf = io.BytesIO()
                shipping.save(buf, format="PNG")

            previews.append(base64.b64encode(buf.getvalue()).decode())

        return JSONResponse({"images": previews})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/")
def home():
    return {"status": "API running 🚀"}