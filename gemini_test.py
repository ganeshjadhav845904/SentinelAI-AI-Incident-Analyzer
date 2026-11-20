import os
from dotenv import load_dotenv
from google import genai

# Load API key
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: Gemini API key not found.")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents="Reply with exactly: SentinelAI Gemini AI Connected Successfully"
        )

        print("\nSUCCESS!")
        print(response.text)

    except Exception as e:
        print("\nGEMINI CONNECTION ERROR:")
        print(str(e))