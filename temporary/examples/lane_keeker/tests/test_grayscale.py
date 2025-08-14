import cv2

image_rgb = cv2.imread('..\\data\\test_image.jpg')
image_gs = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

cv2.imshow('result', image_gs)
cv2.waitKey(0)