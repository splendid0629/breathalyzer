import serial
import subprocess
import time
import mysql.connector
import firebase_admin
from firebase_admin import credentials, db, firestore, storage
import cv2
import face_recognition

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=3)

db_mysql = mysql.connector.connect(
    host="localhost",
    user="hs",
    password="1234",
    database="bre"
)

cred = credentials.Certificate("/home/hs/mykey1.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'gs://brea-6af3b.appspot.com',
    'databaseURL': 'https://brea-6af3b-default-rtdb.firebaseio.com/'
})

bucket_name = 'brea-6af3b.appspot.com'
bucket = storage.bucket(bucket_name)
ref = db.reference('/')

db_firestore = firestore.client()

cursor = db_mysql.cursor()

image_count = 1

def capture_image():
    global image_count
    filename = "image" + str(image_count) + ".jpg"
    cmd = "raspistill -o " + filename + " -w 1280 -h 720"
    subprocess.call(cmd, shell=True)
    image_count += 1

def record_video():
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    h264_filename = "video-" + current_time.replace(" ", "-").replace(":", "") + ".h264"
    mp4_filename = "video-" + current_time.replace(" ", "-").replace(":", "") + ".mp4"
    cmd = "raspivid -o " + h264_filename + " -t 10000 -w 1280 -h 720 -fps 30 -lev 42"
    subprocess.call(cmd, shell=True)
    cmd_convert = "ffmpeg -i " + h264_filename + " -c:v copy " + mp4_filename
    subprocess.call(cmd_convert, shell=True)
    return mp4_filename

def save_video_link(filename, timestamp, max_value):
    if filename == "no_video_available":
        print("No video available.")
        file_url = ""
    else:
        file_path = "./" + filename
        blob = bucket.blob("videos/" + filename)
        blob.upload_from_filename(file_path, content_type='video/mp4')
        print("File uploaded to Firebase Storage:", filename)
        file_url = blob.public_url

    ref.child('video_links').push({
        'filename': filename,
        'url': file_url,
        'timestamp': timestamp,
        'control_value': 'O' if max_value < 0.03 else 'X'
    })
    print("Video link saved:", file_url)
    print("Timestamp saved:", timestamp)
    
    if file_url:
        ref.child('video').set(file_url)
    else:
        ref.child('video').set("")

    ref.child('data').set({
        'user': '이효석',
        'control_value': 'O' if max_value < 0.03 else 'X',
        'value': max_value,
        'timestamp': timestamp
    })
    print("Latest video link and data updated in Realtime Database")

    if max_value >= 0.03:
        first()

    
def save_sensor_value(max_value):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    db_firestore.collection('sensor_values').add({
        'value': max_value,
        'control_value': 'O' if max_value < 0.03 else 'X',
        'user': '이효석',
        'timestamp': current_time
    })
    print("USER: 이효석")
    print("Max value saved:", max_value)
    print("Control value saved:", 'O' if max_value < 0.03 else 'X')
    if max_value < 0.03:
        ser.write(b'G')
    else:
        ser.write(b'R')


   
       

def send_alert():
    print("시동을 종료합니다.")
    ser.write(b'R')

def first():
    ser.flushInput()
    
    while True:
        line = ser.readline().decode().strip()
        if line.startswith("Max Value:"):
            try:
                max_value = float(line.split(":")[1].strip())
            except ValueError:
                print("Invalid max value:", line)
                continue
            save_sensor_value(max_value)
            if max_value >= 0.03:
                save_video_link("no_video_available", time.strftime("%Y-%m-%d %H:%M:%S"), max_value)
                break

        elif line == "record":
            capture_image()
            video_filename = record_video()
            capture_image()
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            if max_value is not None:  
                save_video_link(video_filename, current_time, max_value)
            else:
                print("Max value is not available.")
            break
    db_mysql.close()
    realtime_camera()


def realtime_camera():
    video_capture = cv2.VideoCapture(0)
    last_seen = time.time()
    person_detected = False


    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        face_locations = face_recognition.face_locations(small_frame)
        if face_locations:
            last_seen = time.time()
            person_detected = True

            
        elif person_detected and time.time() - last_seen > 10:
            send_alert()
            person_detected = False
            break
        for (top, right, bottom, left) in face_locations:
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    video_capture.release()
    cv2.destroyAllWindows()
    first()

first()
