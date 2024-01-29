import cv2
import os
from flask import Flask, request, render_template, session, redirect, jsonify
from flask_session import Session
from datetime import date
from datetime import datetime
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import joblib
from random import randint
from flask_sqlalchemy import SQLAlchemy
from dataclasses import dataclass
import base64
from io import BytesIO
from PIL import Image
from sqlalchemy.sql import func
from flask_admin import Admin
from admin import AdminView


basedir = os.path.abspath(os.path.dirname(__file__))


# Defining Flask App
app = Flask(__name__)

# session data (saves variables accross route changes)
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object(__name__)
Session(app)


# connecting to sqlite database with sqlalchemy orm
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# database model for User table
@dataclass
class User(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), nullable=False)
    user_id: str = db.Column(db.String(100), nullable=False)
    role: str = db.Column(db.String(100), default="staff")
    created_at: any = db.Column(db.DateTime(timezone=True),
                                server_default=func.now())

# database model for log table
@dataclass
class Log(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), nullable=False)
    user_id: str = db.Column(db.String(100), nullable=False)
    time = db.Column(db.Time, nullable=False)
    access_type: str = db.Column(db.String(10))
    created_at: any = db.Column(db.DateTime(timezone=True),
                                server_default=func.now())


# admin panel implementation
admin = Admin(app, name='Intelligent Access Control System')
admin.add_view(AdminView(User, db.session, name="Users"))
admin.add_view(AdminView(Log, db.session, name="Logs"))



# Saving Date today in 2 different formats
datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")


# Initializing VideoCapture object to access WebCam
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
try:
    ap = cv2.VideoCapture(1)
except:
    cap = cv2.VideoCapture(0)


# generate unique user id
def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)


# If these directories don't exist, create them
if not os.path.isdir('static'):
    os.makedirs('static')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')
if not os.path.isdir('static/fingerprints'):
    os.makedirs('static/fingerprints')


# get fingerprints keypoints
async def sift_points(img):
    # variables for fingerprint recognition
    best_score = 0
    fileName = None
    image, user = None, None
    kp1, kp2, mp = None, None, None
    for file in [file for file in os.listdir("static/fingerprints")]:
        fingerprint_image = cv2.imread("static/fingerprints/" + file)
        # scale-invariant feature transform (SIFT) algorithm
        sift = cv2.SIFT_create()
        keypoints_1, descriptors_1 = sift.detectAndCompute(img, None)
        keypoints_2, descriptors_2 = sift.detectAndCompute(
            fingerprint_image, None)
        # fast library for approx best match KNN
        matches = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 10}, {}).knnMatch(
            descriptors_1, descriptors_2, k=2)

        match_points = []

        for p, q in matches:
            if p.distance < 0.65 * q.distance:
                match_points.append(p)

        keypoints = 0

        if (len(keypoints_1) <= len(keypoints_2)):
            keypoints = len(keypoints_1)
        else:
            keypoints = len(keypoints_2)

        if len(match_points) / keypoints * 100 > best_score:
            best_score = len(match_points) / keypoints * 100
            fileName = file
            image = fingerprint_image
            kp1, kp2, mp = keypoints_1, keypoints_2, match_points

    print("Best match:  " + fileName)
    print("Best score:  " + str(best_score))

    if len(match_points) > 0:
        user_id = fileName.split("_")[0]
        user = User.query.filter(User.user_id == user_id).first()
        print(user)
        user_name = user.name + '_' + user.user_id
        print(user_name)
        return {"user": user, "user_id":user_name}

    return {"user": user, "user_id": ""}


# read base64 data to cv2 type
def readb64(uri):
    encoded_data = uri.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# store base64 fingerprint data as png file in storage


def saveFinger(finger, user_id, type):
    starter = finger.find(',')
    image_data = finger[starter+1:]
    image_data = bytes(image_data, encoding="ascii")
    im = Image.open(BytesIO(base64.b64decode(image_data)))
    if type == 0:
        im.save(f'static/fingerprints/{user_id}_left.png')
    else:
        im.save(f'static/fingerprints/{user_id}_right.png')


# get a number of total registered users
def totalreg():
    result = User.query.count()
    return result


# extract the face from an image
def extract_faces(img):
    if img != []:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.3, 5)
        return face_points
    return []


# Identify face using ML model
def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    return model.predict(facearray)


# A function which trains the model on all the faces available in faces folder
def train_model():
    faces = []
    labels = []
    userlist = os.listdir('static/faces')
    for user in userlist:
        for imgname in os.listdir(f'static/faces/{user}'):
            img = cv2.imread(f'static/faces/{user}/{imgname}')
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces, labels)
    joblib.dump(knn, 'static/face_recognition_model.pkl')


# Add Attendance of a specific user
def add_attendance(name):
    username = name.split('_')[0]
    userid = name.split('_')[1]
    current_time = datetime.time(datetime.now())

    logs = Log.query.filter(Log.user_id == userid, func.DATE(
        Log.created_at) == date.today()).order_by(Log.created_at.desc()).first()

    log = Log(name=username, user_id=userid,
              time=current_time, created_at=datetime.now())

    if logs is None:
        log.access_type = 'Entry'
        db.session.add(log)
        db.session.commit()
    elif logs.access_type == 'Entry':
        log.access_type = 'Exit'
        db.session.add(log)
        db.session.commit()
    elif logs.access_type == 'Exit':
        log.access_type = 'Entry'
        db.session.add(log)
        db.session.commit()


# get access logs for today
def get_logs():
    logs = Log.query.filter(func.DATE(
        Log.created_at) == date.today()).all()
    return logs


################## ROUTING FUNCTIONS #########################

# Our main page
@app.route('/')
def home():
    logs = get_logs()
    return render_template('home.html', logs=logs, totalreg=totalreg(), datetoday2=datetoday2)


# Our registeration page
@app.route('/register')
def register():
    return render_template('add.html', totalreg=totalreg(), datetoday2=datetoday2)


# This function will run when we click on Take Biometric Button
@app.route('/start')
def start():
    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template('home.html', totalreg=totalreg(), datetoday2=datetoday2, mess='There is no trained model in the static folder. Please capture user biometrics to continue.')

    cap = cv2.VideoCapture(0)
    ret = True
    while ret:
        ret, frame = cap.read()

        if not ret:
            break
        else:
            if extract_faces(frame) != ():
                (x, y, w, h) = extract_faces(frame)[0]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
                face = cv2.resize(frame[y:y+h, x:x+w], (50, 50))
                identified_person = identify_face(face.reshape(1, -1))[0]

                add_attendance(identified_person)
                cv2.putText(frame, f'{identified_person}', (30, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
                cv2.imshow('Access Control', frame)

                if cv2.waitKey(3000) or 0xFF == ord('q'):
                    break
            else:
                cv2.imshow('Access Control', frame)

                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break

    cap.release()
    cv2.destroyAllWindows()

    logs = get_logs()

    return render_template('home.html', open=True, name=identified_person.split('_')[0], logs=logs, totalreg=totalreg(), datetoday2=datetoday2)


# This function will run when we register a new user facial biometrics
@app.route('/add', methods=['GET', 'POST'])
def add():
    newusername = request.form['newusername']
    newuserid = random_with_N_digits(5)
    # adding userid to session
    session['userid'] = newuserid

    # # starting facial biometric enrollment
    # userimagefolder = 'static/faces/'+newusername+'_'+str(newuserid)
    # if not os.path.isdir(userimagefolder):
    #     os.makedirs(userimagefolder)
    # cap = cv2.VideoCapture(0)
    # i, j = 0, 0
    # while 1:
    #     _, frame = cap.read()
    #     faces = extract_faces(frame)
    #     for (x, y, w, h) in faces:
    #         cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
    #         cv2.putText(frame, f'Images Captured: {i}/50', (30, 30),
    #                     cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
    #         if j % 10 == 0:
    #             name = newusername+'_'+str(i)+'.jpg'
    #             cv2.imwrite(userimagefolder+'/'+name, frame[y:y+h, x:x+w])
    #             i += 1
    #         j += 1
    #     if j == 500:
    #         break
    #     cv2.imshow('Enrolling new User', frame)
    #     if cv2.waitKey(1) == 27:
    #         break
    # cap.release()
    # cv2.destroyAllWindows()
    # print('Training Model')
    # # train model using captured images
    # train_model()
    # adding user to database
    user = User(name=newusername, user_id=newuserid,
                created_at=datetime.now())
    db.session.add(user)
    db.session.commit()

    # redirect to fingerprint enrollment screen , user_id passed in session
    return redirect('/fingerprint')


# This function will run when we register a new user fingerprint biometrics
@app.route('/fingerprint', methods=['GET', 'POST'])
def addFingers():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        left_finger = request.form.get('left_finger')
        right_finger = request.form.get('right_finger')
        try:
            saveFinger(left_finger, user_id=user_id, type=0)
            saveFinger(right_finger, user_id=user_id, type=1)
        except:
            print("An exception occurred")
        return "success"
    else:
        # user id retrieved from session
        user_id = session.get('userid')
        return render_template('fingerprint.html', user_id=user_id)


# This function will run when we register a new user facial biometrics
@app.route('/verify', methods=['POST'])
async def verifyFinger():
    user = None
    response = {}
    userdata = {}
    fingeprint = request.form.get('fingerprint')
    img = readb64(fingeprint)
    try:
        userdata = await sift_points(img)
        if userdata['user'] is not None:
            add_attendance(userdata['user_id'])
            response = jsonify({'message': 'Access Granted',
                            'success': True, 'user': userdata['user']})
            response.status_code = 201
        else:
            response = jsonify({'message': 'Access Denied',
                            'success': False, 'user': user})
            response.status_code = 201
    except:
        print("An exception occurred")  

    return response


# Our main function which runs the Flask App
if __name__ == '__main__':
    with app.app_context():
        # create database tables if not exist
        db.create_all()
    app.run(debug=True)
