import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Or paste your key directly for testing

def fetch_gemini_questions(job, difficulty, count, qtype="mcq"):
    """
    Generate questions using Google Gemini.
    qtype: "mcq" or "theoretical"
    """
    if not GEMINI_API_KEY:
        return ["Gemini API key not set."]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")

    if qtype == "mcq":
        prompt = (
            f"Generate {count} multiple-choice interview questions for a {job} role. "
            f"Difficulty: {difficulty}. "
            f"Each question should have 4 options and indicate the correct answer. "
            f"Return as a numbered list."
        )
    else:
        prompt = (
            f"Generate {count} practical or theoretical interview questions for a {job} role. "
            f"Difficulty: {difficulty}. "
            f"Return as a numbered list."
        )

    try:
        response = model.generate_content(prompt)
        return response.text.strip().split('\n')
    except Exception as e:
        return [f"Error from Gemini: {e}"]

# Example usage:
if __name__ == "__main__":
    # Set your API key for testing
    os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY"
    questions = fetch_gemini_questions("Software Engineer", "medium", 3, qtype="mcq")
    for q in questions:
        print(q)