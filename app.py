"""Entry point for Hugging Face Spaces (Gradio SDK runs this file).

Set GROQ_API_KEY as a Space secret. Locally you can also just run
`python -m fantsu.web`.
"""

from fantsu.web import build_app

demo = build_app()

if __name__ == "__main__":
    demo.launch()
