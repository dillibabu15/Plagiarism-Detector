from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pdfplumber
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx'}

# Ensure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def read_file(filepath):
    """Read text from TXT, PDF, or DOCX files."""
    if filepath.endswith('.pdf'):
        text = ''
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        return text
    elif filepath.endswith('.docx'):
        doc = Document(filepath)
        return '\n'.join([para.text for para in doc.paragraphs])
    else:  # TXT file
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

def preprocess(text):
    """Preprocess text: lowercase, tokenize, remove stopwords."""
    text = text.lower()
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    filtered = [word for word in tokens if word.isalnum() and word not in stop_words]
    return ' '.join(filtered)

def calculate_similarity(documents):
    """Calculate similarity matrix using TF-IDF and cosine similarity."""
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)
    return cosine_similarity(tfidf_matrix)

def generate_pdf_report(results, filename='report.pdf'):
    """Generate a PDF report of the similarity results."""
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    y = 750  # Starting Y position
    c.drawString(50, y, "Plagiarism Report")
    y -= 30
    
    for i, row in enumerate(results['matrix']):
        line = f"Document {i+1}: " + " ".join(f"{val*100:.1f}%" for val in row)
        c.drawString(50, y, line)
        y -= 20
    
    c.save()
    return filename

@app.route('/')
def index():
    """Render the file upload page."""
    return render_template('upload.html')

@app.route('/check', methods=['POST'])
def check_plagiarism():
    """Handle file uploads and compute plagiarism."""
    if 'files' not in request.files:
        return "No files uploaded", 400
    
    files = request.files.getlist('files')
    filenames = []
    documents = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            text = read_file(filepath)
            processed = preprocess(text)
            documents.append(processed)
            filenames.append(filename)
    
    if len(documents) < 2:
        return "Need at least 2 documents to compare", 400
    
    similarity_matrix = calculate_similarity(documents)
    results = {
        'filenames': filenames,
        'matrix': similarity_matrix.tolist()
    }
    
    report_path = generate_pdf_report(results)
    return render_template('results.html', results=results, report=report_path)

@app.route('/download/<filename>')
def download(filename):
    """Allow users to download the PDF report."""
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)