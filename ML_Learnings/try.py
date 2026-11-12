import cv2
import numpy as np

img = cv2.imread('bricks.jpg', 1) 
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

kernel = np.ones((5,5), np.uint8)    
img_dilated = cv2.dilate(gray, kernel, iterations=1)

laplacian = cv2.Laplacian(img_dilated,cv2.CV_64F)


# Python program to convert
# numpy laplacian to image

# import required libraries
import numpy as np
from PIL import Image as im


# create a numpy laplacian from scratch
# using arange function.
# 1024x720 = 737280 is the amount
# of pixels.
# np.uint8 is a data type containing
# numbers ranging from 0 to 255
# and no non-negative integers
# laplacian = np.arange(0, 737280, 1, np.uint8)

# check type of laplacian
print(type(laplacian))

# our laplacian will be of width
# 737280 pixels That means it
# will be a long dark line
print(laplacian.shape)

# Reshape the laplacian into a
# familiar resoluition
# laplacian = np.reshape(laplacian, (1024, 720))

# show the shape of the laplacian
print(laplacian.shape)

# show the laplacian
print(laplacian)

# creating image object of
# above laplacian
data = im.fromarray(laplacian)
print(data)
if data.mode != 'RGB':
    data = data.convert('RGB')
# saving the final output
# as a PNG file
# data.save('new_bricks.jpg')


