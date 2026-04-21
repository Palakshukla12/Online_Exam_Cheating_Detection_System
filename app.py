from flask import Flask, render_template, request, redirect, session, Response
import cv2
import time
from ai.detector import detect_cheating

app = Flask(__name__)
app.secret_key = "exam_secret_key"

# ---------------- CAMERA ----------------
camera = cv2.VideoCapture(0)

# ---------------- SYSTEM VARIABLES ----------------
warnings = 0
MAX_WARNINGS = 20
WARNING_COOLDOWN = 5
last_warning_time = 0
exam_active = True


# ---------------- LOGIN ----------------
@app.route('/')
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def do_login():
    session['user'] = request.form['username']
    return redirect('/dashboard')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')


# ---------------- EXAM PAGE ----------------
@app.route('/exam')
def exam():
    if 'user' not in session:
        return redirect('/')
    return render_template('exam.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------- WARNING SYSTEM ----------------
def add_warning(points, current_time):
    global warnings, last_warning_time

    if current_time - last_warning_time >= WARNING_COOLDOWN:
        warnings += points
        last_warning_time = current_time


# ---------------- VIDEO STREAM ----------------
def gen_frames():

    global warnings, exam_active

    while True:

        success, frame = camera.read()
        if not success or frame is None:
            continue

        status, count = detect_cheating(frame)
        current_time = time.time()

        # ---------------- DEFAULT ----------------
        display_text = "FACE OK - NORMAL"
        color = (0, 255, 0)

        # ---------------- AI DETECTION ----------------
        if exam_active:

            if status == "NO_FACE":
                display_text = "NO FACE DETECTED"
                color = (0, 0, 255)
                add_warning(1, current_time)

            elif status == "MULTIPLE_FACES":
                display_text = f"MULTIPLE FACES ({count})"
                color = (0, 0, 255)
                add_warning(2, current_time)

            elif status == "PHONE_DETECTED":
                display_text = "PHONE DETECTED ⚠"
                color = (0, 0, 255)
                add_warning(3, current_time)

        # ---------------- TERMINATION ----------------
        if warnings >= MAX_WARNINGS:
            exam_active = False
            display_text = "EXAM TERMINATED"
            color = (0, 0, 255)

        # ---------------- UI ----------------
        cv2.rectangle(frame, (20, 20), (650, 140), (0, 0, 0), -1)

        cv2.putText(frame, display_text, (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.putText(frame, f"Warnings: {warnings}/{MAX_WARNINGS}", (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # ---------------- FRAME ----------------
        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ---------------- VIDEO ROUTE ----------------
@app.route('/video')
def video():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ---------------- SUBMIT EXAM (IMPORTANT FIX) ----------------
@app.route('/submit', methods=['POST'])
def submit():

    global exam_active

    exam_active = False   # stop exam

    return redirect('/result')


# ---------------- RESULT PAGE ----------------
@app.route('/result')
def result():

    global warnings

    status = "PASS" if warnings < MAX_WARNINGS else "FAIL"

    return render_template(
        'result.html',
        warnings=warnings,
        max_warnings=MAX_WARNINGS,
        status=status
    )


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)