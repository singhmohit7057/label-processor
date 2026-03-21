import fitz
from PIL import Image
import gc

def pdf_to_images(pdf_bytes):
    """Converts PDF bytes to a list of PIL Images using PyMuPDF."""
    doc = None
    images = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            # Convert to 'L' (Grayscale) immediately to save 66% RAM
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("L")
            images.append(img)
        return images
    finally:
        if doc:
            doc.close()
        gc.collect()

def process_page(img, size):
    """Crops and resizes a single page into a Shipping Label and Invoice."""
    # 300 DPI dimensions
    SHIPPING_DIM = (900, 1500) if size == "3x5" else (1200, 1800)
    INVOICE_DIM = (1200, 1800)

    w, h = img.size

    # 1. Shipping Label Crop (Top 46%)
    shipping = img.crop((0, int(h * 0.02), w, int(h * 0.462)))
    shipping = shipping.resize(SHIPPING_DIM, Image.Resampling.LANCZOS)

    # 2. Invoice Crop (Bottom rotated)
    rotated = img.rotate(90, expand=True)
    rw, rh = rotated.size
    invoice = rotated.crop((
        int(rw * 0.385),
        int(rh * 0.07),
        int(rw * 0.95),
        int(rh * 0.92)
    ))
    invoice = invoice.resize(INVOICE_DIM, Image.Resampling.LANCZOS)

    return shipping, invoice