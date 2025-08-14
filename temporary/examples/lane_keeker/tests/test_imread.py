import cv2

image = cv2.imread('..\\data\\test_image.jpg')
cv2.imshow('result', image)
cv2.waitKey(0)