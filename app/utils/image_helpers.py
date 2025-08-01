# app/utils/image_helpers.py
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2

def preprocess_receipt(path, output_path=None):
    # 1) Load and convert to grayscale
    img = Image.open(path).convert("L")

    # 2) Increase contrast
    img = ImageOps.autocontrast(img, cutoff=2)

    # 3) Apply a slight sharpening filter
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # 4) Convert to OpenCV for thresholding + deskew
    arr = np.array(img)
    # adaptive threshold to binarize
    binarized = cv2.adaptiveThreshold(arr, 255,
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY,
                                      blockSize=35,
                                      C=10)
    # 5) (Optional) deskew by finding the largest contour
    coords = np.column_stack(np.where(binarized < 255))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    (h, w) = binarized.shape
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    deskewed = cv2.warpAffine(binarized, M, (w, h),
                              flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 6) Save or return PIL image
    pil_img = Image.fromarray(deskewed)
    if output_path:
        pil_img.save(output_path)
    return pil_img

