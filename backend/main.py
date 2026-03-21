from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import zipfile
import gc

from processor import pdf_to_images, process_page

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change this to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process")
async def process(
    file: UploadFile = File(...),
    size: str = Form("4x6"),
    output: str = Form("separate"),
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
                        zipf.writestr(f"shipping_{i}.pdf", sb.getvalue())
                        zipf.writestr(f"invoice_{i}.pdf", ib.getvalue())
                    else:
                        cb = io.BytesIO()
                        s.save(cb, "PDF", save_all=True, append_images=[inv])
                        zipf.writestr(f"combined_{i}.pdf", cb.getvalue())
            
            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=labels.zip"}
            )

        # Default: Return first page as a combined PDF if ZIP is disabled
        s, inv = process_page(pages[0], size)
        buffer = io.BytesIO()
        s.save(buffer, "PDF", save_all=True, append_images=[inv])
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        gc.collect()

@app.post("/preview")
async def preview(file: UploadFile = File(...), size: str = Form("4x6")):
    try:
        pdf_bytes = await file.read()
        pages = pdf_to_images(pdf_bytes)
        
        # Only preview the first page to save bandwidth
        shipping, invoice = process_page(pages[0], size)
        
        import base64
        results = []
        for img in [shipping, invoice]:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            results.append(base64.b64encode(buf.getvalue()).decode())
            
        return {"images": results}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        gc.collect()

@app.get("/")
def health():
    return {"status": "online"}