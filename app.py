import streamlit as st
import fitz  # PyMuPDF
import requests
import io
import re

st.set_page_config(page_title="CV Optimizer", layout="centered")
st.title("📄 CV Optimizer with JD-based Summary & Skills (Ollama)")
st.info("💡 Note: You must have Ollama running locally with a 'llama3' model to use this tool.")

uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
jd_text = st.text_area("Paste the Job Description (JD)", height=200)

# Define common CV section headings to prevent over-extraction of content
# This list is crucial for determining where one section ends and another begins.
common_cv_section_headings = [
    r"^(Experience|Work Experience|Professional Experience)\s*$",
    r"^(Education|Academic Background)\s*$",
    r"^(Skills|Technical Skills|Key Skills|Core Competencies)\s*$",
    r"^(Projects|Portfolio|Research Projects)\s*$",
    r"^(Certifications|Licenses)\s*$",
    r"^(Awards|Honors)\s*$",
    r"^(Publications|Research)\s*$",
    r"^(Languages)\s*$",
    r"^(Interests|Hobbies)\s*$",
    r"^(Contact|Contact Information)\s*$",
    r"^(Volunteer Experience|Volunteering)\s*$",
    r"^(References)\s*$",
    # Include Summary/Objective itself for robust pattern matching, but ensure
    # it's not the 'next' heading when searching for content for itself.
    r"^(Summary|Objective)\s*$" 
]

def find_heading_and_content_area(page, heading_pattern, all_section_patterns):
    """
    Finds a specific heading and precisely defines the content area immediately following it.
    The content area's lower bound is determined by the start of the next major section heading.
    
    Returns: (heading_block_data, heading_rect, content_rect, content_text)
    - heading_block_data: The raw PyMuPDF block data for the heading.
    - heading_rect: The bounding box for the heading text.
    - content_rect: The precise bounding box for the content area below the heading.
    - content_text: The text extracted from within the content_rect.
    """
    blocks = page.get_text("blocks")
    
    heading_block = None
    heading_idx = -1
    # 1. Find the target heading block
    for i, block in enumerate(blocks):
        text = block[4].strip()
        if re.match(heading_pattern, text, re.IGNORECASE):
            heading_block = block
            heading_idx = i
            break

    if not heading_block:
        return None, None, None, None

    heading_rect = fitz.Rect(heading_block[:4])
    
    # 2. Determine the vertical extent of the content area
    content_y0 = heading_rect.y1 # Start immediately below the heading
    content_y1 = page.rect.y1 # Default to bottom of the page if no next heading found

    # Find the next major section heading to define the lower bound of content_y1
    found_next_heading_y0 = None
    for i in range(heading_idx + 1, len(blocks)):
        current_block = blocks[i]
        current_block_text = current_block[4].strip()

        is_next_section_heading = False
        for pattern in all_section_patterns:
            # Ensure it's a *different* heading than the one we are currently processing
            if re.match(pattern, current_block_text, re.IGNORECASE) and not re.match(heading_pattern, current_block_text, re_IGNORECASE):
                is_next_section_heading = True
                break
        
        # Additionally, check if the block looks like a major heading (e.g., all caps, short, high Y position)
        # This acts as a fallback if the regex patterns aren't exhaustive for all CVs.
        if not is_next_section_heading: # Only apply heuristic if not already matched by pattern
            if len(current_block_text.split()) < 6 and current_block_text.isupper() or \
               (current_block_text and current_block_text[0].isupper() and all(word[0].isupper() for word in current_block_text.split() if word.isalpha())):
                # Heuristic for potential new section heading (e.g., "PROFESSIONAL EXPERIENCE")
                # Ensure it's not just a single capitalized word in a sentence.
                if current_block_text.strip() != "": # Avoid empty strings
                    is_next_section_heading = True

        if is_next_section_heading:
            found_next_heading_y0 = current_block[1] # Top Y-coordinate of the next heading
            break
            
    # Set the precise lower bound for content_y1
    if found_next_heading_y0 is not None:
        content_y1 = found_next_heading_y0 - 5 # Set y1 slightly above the next heading's start

    # Define the precise content_rect based on determined Y coordinates and reasonable X coordinates
    # We use heading_rect.x0 for left and page.rect.x1 - some_margin for right to allow flexibility
    # A default right margin of 50 is used.
    content_rect = fitz.Rect(heading_rect.x0, content_y0, page.rect.x1 - 50, content_y1)

    # 3. Extract text blocks that fall within this defined content_rect
    content_text = ""
    for i in range(heading_idx + 1, len(blocks)):
        current_block = blocks[i]
        current_block_rect = fitz.Rect(current_block[:4])
        
        # Only add block text if its entirely or mostly within the content_rect's vertical range
        # and not significantly below the defined content_rect's bottom.
        if current_block_rect.y0 < content_rect.y1 and current_block_rect.y1 > content_rect.y0:
            content_text += current_block[4] + "\n"
        elif current_block_rect.y0 >= content_rect.y1: # Block is below or at the defined content area's bottom
            break # Stop processing blocks

    # Handle case where no content was found but a region for insertion is needed.
    # This ensures a valid rectangle for insertion even if original content was empty.
    if not content_text.strip():
        # Adjust content_rect to be a reasonable size for new content if no old content was found
        # but a slot was defined (between current heading and next heading, or to page bottom).
        # We ensure it has a minimum height if it's too squished.
        if content_rect.height < 30: # If the space is very small, give it a default minimal height
            content_rect = fitz.Rect(
                content_rect.x0, content_rect.y0,
                content_rect.x1, content_rect.y0 + 50 # Default height of 50 if too small
            )
    
    return heading_block, heading_rect, content_rect, content_text.strip()

def call_ollama(prompt):
    """Generic function to call Ollama with a given prompt."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False, "options": {"temperature": 0.1}}
        )
        response.raise_for_status()
        return response.json()['response'].strip()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to connect to Ollama. Is it running? Error: {e}")
        st.stop()
        return ""

def call_ollama_summary(cv_text, jd, old_summary_line_count):
    prompt = f"""Rewrite this CV summary or objective to match the Job Description (JD), including JD keywords and relevant skills.
Focus on conciseness. Your rewritten summary should aim to be approximately the same length as the original, ideally fitting within {old_summary_line_count} lines if possible. Do not include a heading.

CV Summary:
{cv_text}

JD:
{jd}

Return ONLY the improved summary (no heading):"""
    return call_ollama(prompt)

def call_ollama_skills(cv_skills, jd):
    prompt = f"""Based on the Job Description (JD), identify and list any technical skills that are missing from the provided CV skills list.
List only the missing skills, each on a new line. Do not include any other text or headings.

CV Skills:
{cv_skills}

JD:
{jd}

Missing Skills:"""
    return call_ollama(prompt)

if st.button("Optimize CV"):
    if uploaded_file and jd_text.strip():
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        first_page = doc[0]
        
        st.info("Starting CV optimization...")

        # --- 1. OPTIMIZE SUMMARY/OBJECTIVE ---
        st.subheader("1. Optimizing Summary/Objective")
        summary_heading_block, summary_heading_rect, summary_content_rect, old_summary = find_heading_and_content_area(
            first_page, r"^(Objective|Summary)\s*$", common_cv_section_headings
        )

        if not summary_heading_block:
            st.error("❌ Could not find an 'Objective' or 'Summary' heading in your CV.")
        else:
            old_summary_line_count = old_summary.count('\n') + 1 if old_summary else 4 # Default to 4 lines if empty
            st.info(f"**Old Summary (approx. {old_summary_line_count} lines):**\n{old_summary or '(none detected, will write a new one)'}")
            
            with st.spinner("Writing new summary with Ollama..."):
                new_summary = call_ollama_summary(old_summary, jd_text, old_summary_line_count)
            
            st.success("**New summary generated!**")
            st.write(new_summary)

            # Redact old summary content. The heading itself is NOT redacted.
            if summary_content_rect: # Ensure we have a rectangle to work with
                first_page.add_redact_annot(summary_content_rect, fill=(1, 1, 1))
                first_page.apply_redactions()
            
            # Insert new summary into the same content area
            first_page.insert_textbox(
                summary_content_rect, new_summary, fontsize=11, fontname="helv", color=(0, 0, 0), align=0
            )

        # --- 2. OPTIMIZE SKILLS SECTION ---
        st.subheader("2. Optimizing Skills")
        skills_heading_block, skills_heading_rect, skills_content_rect, old_skills_text = find_heading_and_content_area(
            first_page, r"^(Skills|Technical Skills|Key Skills|Core Competencies)\s*$", common_cv_section_headings
        )
        
        if not skills_heading_block:
            st.warning("⚠️ Could not find a 'Skills' section. Skipping skills optimization.")
        else:
            st.info(f"**Current Skills:**\n{old_skills_text or '(none detected)'}")

            with st.spinner("Finding missing skills from JD with Ollama..."):
                missing_skills = call_ollama_skills(old_skills_text, jd_text)
            
            if missing_skills:
                st.success("**Found missing skills!**")
                st.write(missing_skills)
                
                # Combine old and new skills, ensuring old skills are preserved.
                # Adding new skills after existing ones, separated by newlines for clarity.
                combined_skills = f"{old_skills_text.strip()}\n{missing_skills}" if old_skills_text else missing_skills
                
                # Redact old skills section and insert combined skills
                if skills_content_rect:
                    first_page.add_redact_annot(skills_content_rect, fill=(1, 1, 1))
                    first_page.apply_redactions()
                first_page.insert_textbox(
                    skills_content_rect, combined_skills, fontsize=11, fontname="helv", color=(0, 0, 0), align=0
                )
            else:
                st.info("✅ No new skills found to add based on the JD.")

        # --- 3. SAVE AND DOWNLOAD NEW PDF ---
        st.subheader("3. Download Optimized CV")
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        buf.seek(0)
        st.download_button("📥 Download Optimized CV", buf, file_name="optimized_cv.pdf", mime="application/pdf")
        
    else:
        st.warning("Please upload a CV and paste the JD!")

st.markdown("---\n_Built with ❤️ using Streamlit, PyMuPDF, and Ollama locally._")
