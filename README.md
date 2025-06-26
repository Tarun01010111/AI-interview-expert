# 🧑‍💼 AI Interview Trainer

Welcome to **AI Interview Trainer** – your all-in-one, AI-powered platform for mastering technical, HR, and resume interviews with instant feedback and voice support.

---

## 🎯 What is AI Interview Trainer?

**AI Interview Trainer** is a Streamlit-based web application designed for **students**, **job seekers**, and **professionals** who want to practice and improve their interview skills. It offers realistic technical and HR interview simulations, resume analysis, and AI-powered explanations — all with optional voice feedback.

---

## 👥 Who Is This For?

### 🎓 Students & Job Seekers  
- Practice technical and HR interviews in a realistic environment.
- Get instant, actionable feedback and model answers.
- Analyze and improve your resume for ATS systems.

### 🧑‍💻 Professionals  
- Prepare for job changes or promotions.
- Sharpen your communication and technical skills.
- Get AI-powered explanations for any technical topic.

---

## 🧠 What Can AI Interview Trainer Do?

### 1. 🎯 **Tech Interview**
- Practice MCQ, theoretical, and practical questions for top companies and roles.
- Get instant scoring, feedback, and model answers.
- Listen to questions and feedback with voice support.

### 2. 👨‍🏫 **AI Teacher**
- Ask any technical question and get a detailed, AI-generated explanation.
- Listen to explanations in your chosen voice.

### 3. 🗣️ **HR Chat**
- Simulate HR interviews with realistic behavioral and situational questions.
- Receive constructive feedback and voice playback.

### 4. 📄 **Resume Analyzer**
- Upload your resume (PDF, DOCX, TXT, or PNG).
- Get ATS-style scoring, missing keywords, suggestions, and a summary.
- Listen to your resume feedback as audio.

### 5. 🔊 **Voice Settings**
- Choose your preferred voice (Male/Female) for all audio features.

---

## 🛠️ Tools and Technologies Used

- **Python 3.8+**
- **Streamlit** – Interactive web app UI
- **Google Gemini (google-generativeai)** – AI question/answer generation and feedback
- **OpenAI** – Whisper audio transcription
- **Murf API** – Text-to-speech (TTS) voice feedback
- **PyTesseract** – OCR for image resumes
- **PyPDF2** – PDF text extraction
- **python-docx** – DOCX text extraction
- **Pillow (PIL)** – Image processing
- **requests** – HTTP requests (e.g., Murf audio download)
- **dotenv** – Environment variable management
- **JSON** – User and interview data storage

---

## 🚀 Installation & Setup

1. **Clone this repository** to your local machine.
2. **Install requirements:**
    ```bash
    pip install streamlit openai google-generativeai python-dotenv pytesseract PyPDF2 python-docx Pillow requests
    ```
3. **Set up API keys** for Gemini, Murf, and OpenAI Whisper (see `.env.example` or set in the app sidebar).
4. **Run the app:**
    ```bash
    streamlit run app.py
    ```

---

## 📁 Folder Structure

```
/app.py                # Main Streamlit app
/murf_integration.py   # Murf TTS integration
/users.json            # User database
/interviews.json       # Interview history
/README.md             # Project documentation
```

---

## 🔑 API Keys Required

- **GEMINI_API_KEY** (Google Generative AI)
- **MURF_API_KEY** (Murf TTS)
- **OPENAI_API_KEY** (for Whisper audio transcription)

Set these as environment variables or enter them in the app sidebar.

---

## 💡 Tips

- Use the "Voice Settings" page to select your preferred voice (Male/Female).
- Resume feedback and AI explanations can be listened to using the audio buttons.
- The Murf API has a 3000 character limit for TTS; long texts are truncated automatically.
- All user data is stored locally in JSON files.

---

**Enjoy your AI-powered interview preparation journey!**
