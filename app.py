from flask import Flask, render_template, request, jsonify, session, redirect
import easyocr
import optimized_model
import firebase_admin
from firebase_admin import credentials, db
import time
import secrets
from jinja2 import Environment

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

cred = credentials.Certificate("Firebase_Service_ACC_KEY.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://paper-evaluation-1b915-default-rtdb.asia-southeast1.firebasedatabase.app'
})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/RenderQuestions', methods=['GET', 'POST'])
def renderQuestions():
    if request.method == 'GET':
        test_title = request.args.get('test_title', '')
        test_data = {}
        if test_title:
            ref = db.reference('/Edit')
            test_data = ref.order_by_child('test_title').equal_to(test_title).get()
            if test_data:
                test_data = test_data[next(iter(test_data))]
        env = Environment()
        env.globals['enumerate'] = enumerate
        return render_template('main.html', test_data=test_data, enumerate=enumerate)

@app.route('/RenderTests', methods=['POST'])
def render_tests():
    if request.method == 'POST':
        user_type = request.form['user_type']
        session['user_type'] = user_type
        return redirect('/RenderTests')

@app.route('/RenderTests', methods=['GET', 'POST'])
def display_tests():
    user_type = session.get('user_type', None)
    if user_type is None:
        return redirect('/')
    ref = db.reference('/Edit') 
    tests = ref.get()
    return render_template('tests.html', user_type=user_type, tests=tests)

@app.route('/RenderSettings', methods=['GET', 'POST'])
def settings():
    test_title = request.args.get('test_title', '')
    ref = db.reference('/Edit')
    test_data = ref.order_by_child('test_title').equal_to(test_title).get()
    if test_data:
        test_key = next(iter(test_data))
        existing_test_data = test_data[test_key]
        enable_scores = existing_test_data.get('settings', {}).get('enable_scores', False)
    else:
        enable_scores = False  # Default settings if not found
    return render_template('settings.html', test_title=test_title, enable_scores=enable_scores)

@app.route('/submit_settings', methods=['POST'])
def submit_settings():
    test_title = request.args.get('test_title', '')
    enable_scores = request.form.get('enable_scores', False)
    ref = db.reference('/Edit')
    test_data = ref.order_by_child('test_title').equal_to(test_title).get()
    if test_data:
        test_key = next(iter(test_data))
        existing_test_data = test_data[test_key]
    else:
        existing_test_data = {}
    existing_test_data['settings'] = {"enable_scores": enable_scores}
    ref.child(test_key).update(existing_test_data)
    print('Settings updated in Firebase Realtime Database')
    ref = db.reference('/Edit') 
    tests = ref.get()
    return render_template('tests.html', user_type=session.get('user_type', None), tests=tests) 

@app.route('/create_new_test')
def create_new_test():
    return render_template('main.html', test_data=None)

@app.route('/submit', methods=['POST'])
def submit():
    test_title = request.form['testTitle']
    EDIT = request.form.get('EDIT', None)
    questions = []
    answers = []
    global qns_cnt
    qns_cnt = int(request.form['questionCount'])
    for i in range(1, int(request.form['questionCount']) + 1):
        question = request.form[f'question{i}']
        answer = request.form[f'answer{i}']
        questions.append(question)
        answers.append(answer)
    ref = db.reference('/Edit')
    
    # Check if the test title already exists
    existing_tests = ref.order_by_child('test_title').equal_to(test_title).get()
    
    if EDIT == "True":
        ref = db.reference('/Edit')
        test_data = ref.order_by_child('test_title').equal_to(test_title).get()
        if test_data:
            test_key = next(iter(test_data))
            existing_test_data = test_data[test_key]
        else:
            existing_test_data = {}
        existing_test_data['question_count'] = len(questions)
        existing_test_data['questions'] = questions
        existing_test_data['answers'] = answers
        existing_test_data['test_title'] = test_title
        ref.child(test_key).update(existing_test_data)
        tests = ref.get()
        return render_template('tests.html', user_type=session.get('user_type', None), tests=tests)
    if existing_tests:
        # If test title exists and user is creating a new test, show error
        if 'test_data' not in request.form and EDIT=="False":
            return render_template('main.html', test_data=None, error="Test title already exists. Please choose a different title.")
        
        # If test title exists and user is editing the test, update the existing test
        for key in existing_tests:
            # Check if the current test title matches the title being edited
            if key != request.form['test_data']:
                return render_template('main.html', test_data=None, error="Test title already exists. Please choose a different title.")
            else:
                ref.child(key).update({
                    'question_count': len(questions),
                    'questions': questions,
                    'answers': answers,
                    'test_title': test_title
                })
    else:
        ref.push({
            'question_count': len(questions),
            'questions': questions,
            'answers': answers,
            'test_title': test_title
        })

    tests = ref.get()
    return render_template('tests.html', user_type=session.get('user_type', None), tests=tests)


@app.route('/RenderUpload', methods=['GET', 'POST'])
def renderUpload():
    test_title = request.args.get('test_title', '')
    test_data = {}
    if test_title:
        ref = db.reference('/Edit')
        test_data = ref.order_by_child('test_title').equal_to(test_title).get()
        if test_data:
            test_data = test_data[next(iter(test_data))]
    return render_template('upload.html', test_data=test_data)

@app.route('/doneUpload', methods=['POST'])
def doneUpload():
    test_title = request.form['testTitle']
    upd_ans = []
    qns = db.reference('Edit').get()
    qns_cnt = 0
    for _, val in qns.items():
        qns_cnt = val['question_count']
    print(f'Question Count: {qns_cnt}')
    for i in range(1, qns_cnt+1):
        ans = request.form.get(f'ans{i}')
        upd_ans.append(ans)
    print(upd_ans)
    ref = db.reference('/Edit')
    test_data = ref.order_by_child('test_title').equal_to(test_title).get()
    if test_data:
        test_key = next(iter(test_data))
        existing_test_data = test_data[test_key]
    else:
        existing_test_data = {}
    existing_test_data['Upld_Ans'] = upd_ans
    ref.child(test_key).update(existing_test_data)
    print('Answers updated in Firebase Realtime Database')
    tests = ref.get()
    return render_template('tests.html', user_type=session.get('user_type', None), tests=tests)


@app.route('/fetch_test_data', methods=['GET'])
def get_questions():
    test_title = request.args.get('test_title', '')
    if not test_title:
        return jsonify({'error': 'Test title not provided'}), 400
    ref = db.reference('Edit')
    data = ref.order_by_child('test_title').equal_to(test_title).get()
    if not data:
        return jsonify({'error': 'Test data not found'}), 404
    test_data = next(iter(data.values()))
    return jsonify({
        'test_title': test_data.get('test_title', ''),
        'question_count': test_data.get('question_count', 0),
        'questions': test_data.get('questions', []),
        'answers': test_data.get('Upld_Ans', ['']*test_data.get('question_count', 0)),
    }), 200



@app.route('/perform_ocr', methods=['POST'])
def perform_ocr():
    global ans_cnt
    if 'file' not in request.files:
        return '', 400
    reader = easyocr.Reader(['en'])
    uploaded_files = request.files.getlist('file')
    for idx, file in enumerate(uploaded_files):
        file_path = f'uploaded_image_{ans_cnt}.jpg'
        file.save(file_path)
        image_path = f'uploaded_image_{ans_cnt}.jpg'
        result = [('', text, _) for _, text, _ in reader.readtext(image_path)]
        answer = ' '.join(rec[1] for rec in result)
        print("OCR Result:", answer)
        ans_cnt += 1
    return answer


@app.route('/RenderScore', methods=['GET', 'POST'])
def renderScore():
    print("In Render Score route")
    test_title = request.args.get('test_title', '')
    return render_template('score_card.html', test_title = test_title)

@app.route('/viewScore', methods=['GET', 'POST'])
def view_score():
    start_total = time.time()
    print("In View Score route")
    test_title = request.args.get('test_title', '')
    if not test_title:
        return jsonify({'error': 'Test title not provided'}), 400
    ref_answers_db = db.reference('Edit').get()
    ref_answers, user_answers, questions, Scores = [], [], [], []
    for _, val in ref_answers_db.items():
        if val['test_title'] == test_title:
            ref_answers = val['answers']
            user_answers = val['Upld_Ans']
            questions = val['questions']
            break
    print("Retrieved Data")
    print(f"Retrieval time took {time.time()-start_total}s")
    print(ref_answers)
    print(user_answers)
    if not ref_answers or not user_answers:
        return jsonify({'error': 'Test data not found'}), 404
    start = time.time()
    model = optimized_model.ShortAnswerGrader()
    for i in range(len(ref_answers)):
        Scores.append(model.calculate(ref_answers[i], user_answers[i]))
    print(f"Model took {time.time()-start}s")
    data = {
        'test_title': test_title,
        'question_count': len(ref_answers),
        'questions': questions,
        'ref_answers': ref_answers,
        'user_answers': user_answers,
        'scores': Scores
    }
    print(data)
    print(f"Total time: {time.time()-start_total}s")
    return render_template("score_card.html", data=data)

if __name__ == '__main__':
    app.run(debug=True)
