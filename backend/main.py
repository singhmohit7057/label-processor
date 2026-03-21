from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from PIL import Image
import io
import zipfile
import fitz  # PyMuPDF

app = FastAPI()

DPI = 300

@app.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    size: str = Form(...),        # 3x5 or 4x6
    output: str = Form(...),      # separate or combined
):
    pdf_bytes = await file.read()

    # =========================
    # 🔁 LOAD PDF WITH PYMUPDF
    # =========================
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # simulate DPI
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)

    SHIPPING_SIZE = (3 * DPI, 5 * DPI) if size == "3x5" else (4 * DPI, 6 * DPI)
    INVOICE_4x6 = (4 * DPI, 6 * DPI)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, img in enumerate(pages, start=1):
            w, h = img.size

            # =========================
            # 📦 SHIPPING
            # =========================
            shipping = img.crop((0, int(h*0.02), w, int(h*0.462)))
            shipping = shipping.resize(SHIPPING_SIZE).convert("RGB")

            # =========================
            # 🧾 INVOICE
            # =========================
            rotated = img.rotate(90, expand=True)
            rw, rh = rotated.size

            invoice = rotated.crop((
                int(rw*0.385),
                int(rh*0.07),
                int(rw*0.95),
                int(rh*0.92)
            ))
            invoice = invoice.resize(INVOICE_4x6).convert("RGB")

            # =========================
            # 💾 SAVE
            # =========================
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

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=output.zip"}
    )