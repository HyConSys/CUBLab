import os
import cv2
import numpy
import time
import math
from simple_pid import PID
pid = PID(1, 0.1, 0.05, setpoint=0)

def DEPTH_OF_VESIBILITY(height, width):
    return int(height/3);

# A polygon represening the visibility winodw to be used as a mask
def REGION_OF_VISIBILITY(height, width, turn_skew): 
    H = height-1
    W = width-1
    shoulder_skew = int(turn_skew/2)
    depth = DEPTH_OF_VESIBILITY(height, width)
    return [(0, H), (W, H), (W, (H-150+shoulder_skew)), (430-turn_skew, depth), (210-turn_skew, depth), ((0), (H-150-shoulder_skew)), (0, H)]

# creates two-points line from slopw/intercept
# we limit the lines to start from tgh eimage buttom (hight)
# and end in the middle of the image
def make_coordinates(height, width, line_slope_and_intercept):
    slope ,intercept = line_slope_and_intercept
    y1 = height
    y2 = DEPTH_OF_VESIBILITY(height, width)
    x1 = int((y1-intercept)/slope)
    x2 = int((y2-intercept)/slope)
    return numpy.array([x1, y1, x2, y2])

# puts a mask on the image
# the mask is a polygon defined by REGION_OF_VISIBILITY
def mask_image(image, turn_skew):
    height = image.shape[0]
    width = image.shape[1]
    polygons = numpy.array([REGION_OF_VISIBILITY(height, width, turn_skew)])
    mask = numpy.zeros_like(image)
    cv2.fillPoly(mask, polygons, 255)
    masked_image = cv2.bitwise_and(mask,image)
    return masked_image        

# crates a grayscale-version from the image then enforces a derivative on it
# now, we have a gradient image where those parts of obious change of color
# can be easily identified
def canny(image):
    image_gs = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    ## blur the image using a gaussian blurr matrix of size 5x5
    image_blurred = cv2.GaussianBlur(image_gs, (5,5), 0)
    ## compute the gradient (derivative) of the blurred image
    image_gradient = cv2.Canny(image_blurred, 50, 150)
    return image_gradient

def is_line_entirly_on_left_side(height, width, line):
    x1, y1, x2, y2 = line.reshape(4)
    if x1 <= width/2 and x2 <= width/2:
        return True
    else:
        return False

def is_line_entirly_on_right_side(height, width, line):
    x1, y1, x2, y2 = line.reshape(4)
    if x1 > width/2 and x2 > width/2:
        return True
    else:
        return False

# extract two lanes from the lines detected from the images
# here, we assume we have a view of the camera inside a road with 
# a lane on our left and another lane on our right
# we then split the lines two two groups based on their slopes
def get_two_lanes(image_masked):

    height = image_masked.shape[0]
    width = image_masked.shape[1]

    # extract the lines the the masked region
    lines = cv2.HoughLinesP(image_masked, 2, numpy.pi/180.0, 100, numpy.array([]), minLineLength=40, maxLineGap=5)
    
    right_lines = []
    left_lines = []    

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line.reshape(4)
            params = numpy.polyfit((x1,x2),(y1,y2),1.0)
            slope = params[0]
            intercept = params[1]            

            # filter any horizontal-close lines (those in the range -/+ 20 deg)
            if slope >= -0.35 and slope <= 0.35:
                continue

            if slope <= 0 and is_line_entirly_on_left_side(height, width, line):
                left_lines.append((slope, intercept))
            else:
                if is_line_entirly_on_right_side(height, width, line):
                    right_lines.append((slope, intercept))


    if len(right_lines)==0:
        has_right = False
        right = numpy.array([0, 0, 0, 0])
    else:
        has_right = True
        right_lane_avg = numpy.average(right_lines, axis=0)
        right = make_coordinates(height, width, right_lane_avg)            

    if len(left_lines)==0:
        has_left = False
        left = numpy.array([0, 0, 0, 0])        
    else:
        has_left = True
        left_lane_avg = numpy.average(left_lines, axis=0)
        left = make_coordinates(height, width, left_lane_avg)        

    return lines, has_left, has_right, numpy.array([left, right])


# plots lines on the image with some color
def draw_lines(image, lines, color):
    lane_image = numpy.zeros_like(image)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line.reshape(4)
            cv2.line(lane_image, (int(x1), int(y1)), (int(x2),int(y2)), color, 5)

    return cv2.addWeighted(image, 0.8, lane_image, 1.0, 1.0)

# resizes an image and places it in to the container image
def draw_image(image_container, image_inside):
    scale_percent = 25
    width = int(image_inside.shape[1] * scale_percent / 100)
    height = int(image_inside.shape[0] * scale_percent / 100)  
    dim = (width, height)
    resized = cv2.resize(image_inside, dim, interpolation = cv2.INTER_AREA)

    y_offset = 0
    x_offset = image_container.shape[1] - resized.shape[1]

    y1, y2 = y_offset, y_offset + resized.shape[0]
    x1, x2 = x_offset, x_offset + resized.shape[1]

    image_container[y_offset:y_offset+resized.shape[0], x_offset:x_offset+resized.shape[1], 0] = resized
    image_container[y_offset:y_offset+resized.shape[0], x_offset:x_offset+resized.shape[1], 1] = resized
    image_container[y_offset:y_offset+resized.shape[0], x_offset:x_offset+resized.shape[1], 2] = resized



#-------------------------------------------------------------------------------------------------
# M A I N
#-------------------------------------------------------------------------------------------------
# a value between -75 and 75 to represent the turn of the lane
# we use it to skew the visibility trapzoid
turn_skew = 0 

#video_file = "data" + os.path.sep + "test_video.mp4"
video = cv2.VideoCapture(0)
frame_idx = 0
while(video.isOpened()):
    frame_idx = frame_idx + 1 
    t_start = time.time()

    # grab a frame
    #_, image_rgb = video.read()
    image_rgb = cv2.imread("data" + os.path.sep + "testnew.jpg")
    height = image_rgb.shape[0]
    width = image_rgb.shape[1]

    if frame_idx == 1:
        print('Height: ' + str(image_rgb.shape[0]))
        print('Width: ' + str(image_rgb.shape[1]))

    # calc the gradient and mask the image
    image_grad = canny(image_rgb)
    image_masked = mask_image(image_grad, turn_skew)

    # deduct the two lanes from the extreacted lines
    # keep a memory of last found lanes/use them
    all_lines, has_left, has_right, two_lanes = get_two_lanes(image_masked)
    image_combined = draw_lines(image_rgb, all_lines, (0,0,255))

    if has_left:
        last_left = two_lanes[0]
    else:
        if 'last_left' in locals():
            two_lanes[0] = last_left

    if has_right:
        last_right = two_lanes[1]        
    else:
        if 'last_right' in locals():
            two_lanes[1] = last_right

    image_combined = draw_lines(image_combined, two_lanes, (0,255,0))

    # a virtual center line
    if has_left and has_right:
        both_lines = numpy.array([last_left, last_right])
        center_line =  numpy.average(both_lines, axis=0)
        image_combined = draw_lines(image_combined,  numpy.array([center_line]), (255,0,0))

        # the center line is our control indicator
        # we need to keep it vertical (angle_error == 0)
        angle_error = math.atan2(center_line[2] - center_line[0], center_line[1] - center_line[3])
        angle_error = math.degrees(angle_error)
        if(angle_error <= 2):
            angle_error = 0
        control = pid(angle_error)

    # show FPS    
    t_end = time.time()
    t_seconds = t_end - t_start
    if t_seconds == 0.0:
        cv2.putText(image_combined, ('FPS: Inf. | Frame Idx:' + str(frame_idx)), (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    else:
        fps  = 1.0 / t_seconds
        cv2.putText(image_combined, ('FPS: ' + str(int(fps)) + ' | Frame Idx:' + str(frame_idx)), (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    
    if not has_left or not has_right:
        cv2.putText(image_combined, 'Warninig: Left or right lanes not found.', (10,60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

    # show the mask region in the 
    cv2.polylines(image_combined,numpy.array([REGION_OF_VISIBILITY(height, width, turn_skew)]),False,(255,0,0))

    # picture in picture
    draw_image(image_combined, image_masked)

    # show result
    cv2.imshow('result', image_combined)

    # compute a prespective transformation
    cut_top = 159
    src_points = numpy.float32([[0,cut_top], [width-1,cut_top], [0,height-1], [width-1,height-1]])
    dst_points = numpy.float32([[0,0], [width-1,0], [int(0.4325*width),height-1], [int(0.5675*width),height-1]]) 
    projective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    img_output = cv2.warpPerspective(image_rgb, projective_matrix, (width,height))
    cv2.imshow('result transformed', img_output)
    

    key = cv2.waitKey(1)
    if key == ord('q') or key == ord('Q') or key == 27:
        break

video.release()
cv2.destroyAllWindows()
