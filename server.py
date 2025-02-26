from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF para processamento de PDFs
import openai
import os

# Configuração da API OpenAI
openai.api_key = "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"

app = Flask(__name__)
CORS(app)  # Habilita CORS para permitir comunicação com o frontend

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

pdf_texts = {}  # Dicionário para armazenar o texto extraído dos PDFs
chat_history = []  # Histórico de perguntas e respostas


# Função para extrair texto de um PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text


# Limita o tamanho do texto enviado à IA
def truncate_text(text, max_tokens=4000):
    words = text.split()
    return " ".join(words[:max_tokens]) if len(words) > max_tokens else text


# Rota para fazer upload de múltiplos PDFs
@app.route("/upload", methods=["POST"])
def upload_pdfs():
    if "files[]" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    files = request.files.getlist("files[]")
    if not files:
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        pdf_texts[file.filename] = extract_text_from_pdf(file_path)

    return jsonify({"message": f"{len(files)} arquivos processados com sucesso!"})


# Rota para buscar resposta da IA com base no texto do(s) PDF(s)
@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not pdf_texts:
        return jsonify({"answer": "Nenhum roteiro carregado. Envie um PDF primeiro."})

    combined_text = "\n\n".join(pdf_texts.values())  # Junta todos os textos dos PDFs
    limited_text = truncate_text(combined_text)  # Limita para evitar erro de contexto excessivo

    prompt = f"Baseado no seguinte roteiro operacional, responda:\n\n{limited_text}\n\nPergunta: {question}\nResposta:"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente especializado em análise de documentos."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response["choices"][0]["message"]["content"]

        # Adiciona ao histórico
        chat_history.append({"question": question, "answer": answer})

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)})


# Rota para recuperar o histórico de interações
@app.route("/history", methods=["GET"])
def get_history():
    return jsonify({"history": chat_history})


if __name__ == "__main__":
    app.run(debug=True)
