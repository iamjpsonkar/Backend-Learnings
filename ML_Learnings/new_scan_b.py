import cv2
import numpy as np

from PIL import Image as im

img = cv2.imread('new_bricks.jpg', 1) 
canvas = np.zeros(img.shape, np.uint8)
img2gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

ret,thresh = cv2.threshold(img2gray,128,255,cv2.THRESH_BINARY_INV)
im2,contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)#None

print(len(contours))

for cont in contours:
    cv2.drawContours(canvas, cont, -1, (0, 255, 0), 3)

cv2.imshow('contours',canvas)
cv2.waitKey(30000)
cv2.destroyAllWindows()