from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-text', methods=['POST'])
def process_text():
    data = request.get_json()
    text = data.get('text', '')
    return jsonify({'original_text': text, 'processed_text': text.upper()})

if __name__ == '__main__':
    app.run(debug=True)
