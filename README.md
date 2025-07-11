# CV-Optimizer

This Streamlit application helps users optimize their Curriculum Vitae (CV) by rewriting the "Summary" or "Objective" section and adding missing "Skills" based on a provided Job Description (JD). It leverages a local Ollama instance running the Llama 3 model for text generation.

## Features

* **Summary/Objective Optimization:** Rewrites your CV's summary or objective section to align with the keywords and requirements of a specific Job Description. It aims to maintain the original section's line count for a clean look.
* **Skills Augmentation:** Identifies skills from the Job Description that are missing from your CV's "Skills" section and adds them.
* **PDF Integration:** Reads your CV in PDF format and generates an updated PDF with the optimized content.
* **Local LLM Integration:** Uses Ollama, allowing you to run the language model locally without relying on external APIs (after initial model download).

## Prerequisites

Before running this application, you need to have the following set up:

1.  **Python 3.8+**
2.  **Ollama:**
    * Download and install Ollama from [ollama.com](https://ollama.com/).
    * Once installed, open your terminal/command prompt and pull the `llama3` model:
        ```bash
        ollama pull llama3
        ```
    * Ensure Ollama is running in the background (it usually starts automatically). You can verify by opening your browser and navigating to `http://localhost:11434`.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YourUsername/CV-Optimizer.git](https://github.com/YourUsername/CV-Optimizer.git)
    cd CV-Optimizer
    ```
    *(Replace `YourUsername` with your actual GitHub username and `CV-Optimizer` with your repository name)*

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    * **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Ensure Ollama is running** with the `llama3` model loaded (as per prerequisites).
2.  **Run the Streamlit application:**
    ```bash
    streamlit run Myapp.py
    ```
3.  **Open your web browser:** The application will open in your default web browser (usually at `http://localhost:8501`).
4.  **Upload your CV:** Use the file uploader to select your CV in PDF format.
5.  **Paste the Job Description:** Copy and paste the full Job Description text into the provided text area.
6.  **Click "Optimize CV":** The application will process your CV, rewrite the summary/objective, add missing skills, and provide a downloadable optimized PDF.

## How it Works

The application performs the following steps:

1.  **PDF Parsing:** Uses PyMuPDF (`fitz`) to read the uploaded PDF and extract its text content and block layout.
2.  **Section Identification:** Intelligently identifies the "Summary/Objective" and "Skills" sections by looking for common headings and defining precise content boundaries. This ensures other sections like "Experience" are untouched.
3.  **LLM Interaction:**
    * Sends your existing summary/objective and the JD to your local Ollama instance with a prompt to generate an optimized summary. The prompt guides the LLM to maintain a similar length.
    * Sends your existing skills and the JD to Ollama to identify and list missing skills.
4.  **PDF Modification:**
    * Redacts (effectively erases with a white rectangle) the old content within the identified summary/objective and skills content areas.
    * Inserts the newly generated/combined text into these precise locations.
5.  **PDF Output:** Provides a button to download the modified CV as a new PDF file.

## Limitations

* **PDF Layout Complexity:** The tool works best with standard, cleanly structured CVs. Highly complex layouts (e.g., multi-column skills, heavily stylized text boxes, image-heavy CVs) might yield less precise results for text extraction and insertion.
* **LLM Hallucinations:** While guided by prompts, the LLM might occasionally generate irrelevant information or make minor mistakes. Always review the optimized CV.
* **Line Count Approximation:** The LLM's ability to strictly adhere to an exact line count for the summary is an approximation, as it deals with text content, not visual layout. The `insert_textbox` function will fit the text into the designated space, potentially clipping if the generated text is too long.
* **Ollama Requirement:** Requires a local Ollama server running, which consumes local resources.

---
