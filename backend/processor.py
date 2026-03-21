import fitz
from PIL import Image

def pdf_to_images(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for page in doc:
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    return images


def process_page(img, size):
    SHIPPING = (900, 1500) if size == "3x5" else (1200, 1800)
    INVOICE = (1200, 1800)

    w, h = img.size

    shipping = img.crop((0, int(h * 0.02), w, int(h * 0.462)))
    shipping = shipping.resize(SHIPPING).convert("RGB")

    rotated = img.rotate(90, expand=True)
    rw, rh = rotated.size

    invoice = rotated.crop((
        int(rw * 0.385),
        int(rh * 0.07),
        int(rw * 0.95),
        int(rh * 0.92)
    ))
    invoice = invoice.resize(INVOICE).convert("RGB")

    return shipping, invoice