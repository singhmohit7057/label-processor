import io
import zipfile
import gc
import logging
import traceback
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from processor import pdf_to_images, process_page

# Setup logging for Render console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 1. Clearer, more explicit CORS setup
origins = [
    "https://label-processor.vercel.app", # Your specific frontend
    "http://localhost:5173",              # Local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change this to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Add a manual OPTIONS handler (sometimes required by Render/Vercel)
@app.options("/process")
@app.options("/preview")
@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return Response(status_code=200)

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

        # Single PDF Response
        s, inv = process_page(pages[0], size)
        buffer = io.BytesIO()
        s.save(buffer, "PDF", save_all=True, append_images=[inv])
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf")

    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"❌ PROCESS ERROR:\n{error_stack}")
        return JSONResponse(
            status_code=500, 
            content={"error": str(e), "details": error_stack}
        )
    finally:
        gc.collect()

@app.post("/preview")
async def preview(file: UploadFile = File(...), size: str = Form("4x6")):
    try:
        pdf_bytes = await file.read()
        pages = pdf_to_images(pdf_bytes)
        shipping, invoice = process_page(pages[0], size)
        
        import base64
        results = []
        for img in [shipping, invoice]:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            results.append(base64.b64encode(buf.getvalue()).decode())
            
        return {"images": results}
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"❌ PREVIEW ERROR:\n{error_stack}")
        return JSONResponse(
            status_code=500, 
            content={"error": str(e), "details": error_stack}
        )
    finally:
        gc.collect()


@app.get("/")
async def home():
    return {"status": "online", "message": "Backend is running!"}