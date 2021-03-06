import cv2
from time import sleep


def take_webcam_shot(camera):
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    x = 0
    while True:
        ret, frame = camera.read()
        if x > 4:
            if ret:
                frame = cv2.flip(frame, 1)
                cv2.imwrite("webcam_shot.jpg", frame)
                break
        else:
            x += 1


x = 0

while x < 3:
    camera = cv2.VideoCapture(x)
    if camera.isOpened():
        take_webcam_shot(camera)
        camera.release()
        break
    else:
        x += 1

cv2.destroyAllWindows()
