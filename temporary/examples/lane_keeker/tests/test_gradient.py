import cv2

image_rgb = cv2.imread('..\\data\\test_image.jpg')
image_gs = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

## blur the image using a gaussian blurr matrix of size 5x5
image_blurred = cv2.GaussianBlur(image_gs, (5,5), 0)

## compute the gradient (derivative) of the blurred image
image_gradient = cv2.Canny(image_blurred, 50, 150)

cv2.imshow('result', image_gradient)
cv2.waitKey(0)