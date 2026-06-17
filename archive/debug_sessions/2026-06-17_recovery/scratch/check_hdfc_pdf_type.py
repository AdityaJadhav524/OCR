import fitz

PDF = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"
doc = fitz.open(PDF)
print(f"Pages: {len(doc)}")
for i in range(len(doc)):
    page = doc[i]
    r = page.rect
    images = page.get_images()
    print(f"  Page {i+1}: {r.width:.0f}x{r.height:.0f} pts | images: {len(images)}")
    for img in images[:2]:
        xref = img[0]
        info = doc.extract_image(xref)
        print(f"    Image: {info['width']}x{info['height']} {info['colorspace']} ({info['ext']})")
doc.close()
