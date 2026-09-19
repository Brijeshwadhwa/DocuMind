import os
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_documents(output_dir: str = "./sample_documents"):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Generating sample documents in {output_dir}...")

    # -------------------------------------------------------------
    # 1. Clean Digital PDF (with embedded questions & answer key)
    # -------------------------------------------------------------
    path_01 = os.path.join(output_dir, "01_clean_digital_exam.pdf")
    c = canvas.Canvas(path_01, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(180, 750, "General Science Examination 2026")
    c.setFont("Helvetica", 11)
    c.drawString(50, 725, "Instructions: Choose the correct option for each multiple-choice question.")

    y = 690
    questions_01 = [
        ("1. What is the chemical symbol for Gold?", ["(A) Ag", "(B) Au", "(C) Fe", "(D) Pb"]),
        ("2. Which planet is known as the Red Planet?", ["(A) Venus", "(B) Mars", "(C) Jupiter", "(D) Saturn"]),
        ("3. What is the primary gas found in Earth's atmosphere?", ["(A) Oxygen", "(B) Carbon Dioxide", "(C) Nitrogen", "(D) Hydrogen"]),
        ("4. What is the speed of light in a vacuum approximately?", ["(A) 300,000 km/s", "(B) 150,000 km/s", "(C) 450,000 km/s", "(D) 100,000 km/s"]),
    ]

    for q_text, opts in questions_01:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, q_text)
        y -= 18
        c.setFont("Helvetica", 10)
        c.drawString(70, y, f"{opts[0]}    {opts[1]}")
        y -= 16
        c.drawString(70, y, f"{opts[2]}    {opts[3]}")
        y -= 25

    # Answer Key block
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Answer Key:")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "1-B  2-B  3-C  4-A")

    c.showPage()
    c.save()
    print(f"Created: {path_01}")

    # -------------------------------------------------------------
    # 2. Image-based Question Paper (PNG)
    # -------------------------------------------------------------
    path_02 = os.path.join(output_dir, "02_image_question_paper.png")
    img_width, img_height = 1600, 2000
    img = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    text_lines = [
        "Computer Science Assessment 2026",
        "1. Which data structure operates on a First-In-First-Out (FIFO) basis?",
        "A. Stack",
        "B. Queue",
        "C. Tree",
        "D. Graph",
        "",
        "2. What is the time complexity of binary search on a sorted array?",
        "A. O(n)",
        "B. O(n^2)",
        "C. O(log n)",
        "D. O(1)",
        "",
        "Answer Key:",
        "1. B",
        "2. C"
    ]

    draw.text((450, 80), text_lines[0], fill=(0, 0, 0))
    draw.text((100, 160), text_lines[1], fill=(0, 0, 0))
    draw.text((150, 210), text_lines[2], fill=(0, 0, 0))
    draw.text((150, 260), text_lines[3], fill=(0, 0, 0))
    draw.text((150, 310), text_lines[4], fill=(0, 0, 0))
    draw.text((150, 360), text_lines[5], fill=(0, 0, 0))

    draw.text((100, 440), text_lines[7], fill=(0, 0, 0))
    draw.text((150, 490), text_lines[8], fill=(0, 0, 0))
    draw.text((150, 540), text_lines[9], fill=(0, 0, 0))
    draw.text((150, 590), text_lines[10], fill=(0, 0, 0))
    draw.text((150, 640), text_lines[11], fill=(0, 0, 0))

    draw.text((100, 720), text_lines[13], fill=(0, 0, 0))
    draw.text((100, 770), text_lines[14], fill=(0, 0, 0))
    draw.text((100, 820), text_lines[15], fill=(0, 0, 0))

    png_info = PngImagePlugin.PngInfo()
    png_info.add_text("ocr_text", "\n".join(text_lines))
    img.save(path_02, format="PNG", pnginfo=png_info)
    print(f"Created: {path_02}")

    # -------------------------------------------------------------
    # 3. Scanned / Low-Quality Exam PDF (Simulated scan with noise & low-confidence question)
    # -------------------------------------------------------------
    path_03 = os.path.join(output_dir, "03_scanned_noisy_exam.pdf")
    c3 = canvas.Canvas(path_03, pagesize=letter)
    c3.setFont("Helvetica-Bold", 14)
    c3.drawString(160, 740, "Mathematics Quick Quiz (Scanned Copy)")
    c3.setFont("Helvetica", 10)
    c3.drawString(50, 715, "Subject: Basic Calculus & Algebra")

    y = 670
    c3.setFont("Helvetica-Bold", 10)
    c3.drawString(50, y, "1. What is the derivative of sin(x) with respect to x?")
    y -= 18
    c3.setFont("Helvetica", 9)
    c3.drawString(70, y, "A. -cos(x)    B. cos(x)    C. tan(x)    D. sec(x)")

    # Incomplete/ambiguous question designed to trigger ReviewItem (MALFORMED_OPTIONS / LOW_CONFIDENCE)
    y -= 35
    c3.setFont("Helvetica-Bold", 10)
    c3.drawString(50, y, "2. Solve for x: 2x + 4 = 10.")
    y -= 18
    c3.setFont("Helvetica", 9)
    c3.drawString(70, y, "A. 3")  # Missing options B, C, D to trigger review item

    # Answer Key with an intentional mismatch on Q2 to demonstrate uncertain answer key handling
    y -= 45
    c3.setFont("Helvetica-Bold", 11)
    c3.drawString(50, y, "Answer Key:")
    y -= 18
    c3.setFont("Helvetica", 9)
    c3.drawString(50, y, "1: B    2: Z")  # 'Z' is not in options -> ReviewItem LOW_CONFIDENCE_ANSWER

    c3.showPage()
    c3.save()
    print(f"Created: {path_03}")

    # -------------------------------------------------------------
    # 4. Multi-Page Continuation PDF (Question 2 splits across pages 1 and 2)
    # -------------------------------------------------------------
    path_04 = os.path.join(output_dir, "04_multipage_continuation.pdf")
    c4 = canvas.Canvas(path_04, pagesize=letter)

    # PAGE 1
    c4.setFont("Helvetica-Bold", 14)
    c4.drawString(180, 750, "History Final Examination - Part I")
    c4.setFont("Helvetica-Bold", 11)
    c4.drawString(50, 700, "1. In which year did the Apollo 11 mission land on the Moon?")
    c4.setFont("Helvetica", 10)
    c4.drawString(70, 680, "A. 1965    B. 1969    C. 1972    D. 1975")

    c4.setFont("Helvetica-Bold", 11)
    c4.drawString(50, 620, "2. Which treaty signed in 1919 brought World War I to an official end,")
    c4.drawString(50, 600, "imposing significant reparations on Germany and establishing the League of Nations?")
    c4.setFont("Helvetica", 10)
    c4.drawString(70, 570, "A. Treaty of Paris")
    c4.drawString(70, 550, "B. Treaty of Versailles")
    # Page breaks here while Question 2 options continue on page 2!
    c4.showPage()

    # PAGE 2
    c4.setFont("Helvetica-Bold", 14)
    c4.drawString(180, 750, "History Final Examination - Part II")
    c4.setFont("Helvetica", 10)
    # Remaining options for Question 2
    c4.drawString(70, 700, "C. Treaty of Utrecht")
    c4.drawString(70, 680, "D. Treaty of Ghent")

    c4.setFont("Helvetica-Bold", 11)
    c4.drawString(50, 630, "3. Who was the first President of the United States?")
    c4.setFont("Helvetica", 10)
    c4.drawString(70, 610, "A. Thomas Jefferson    B. Abraham Lincoln    C. George Washington    D. John Adams")

    # Answer key
    c4.setFont("Helvetica-Bold", 11)
    c4.drawString(50, 540, "Answer Key:")
    c4.setFont("Helvetica", 10)
    c4.drawString(50, 520, "1. B   2. B   3. C")

    c4.showPage()
    c4.save()
    print(f"Created: {path_04}")

    # -------------------------------------------------------------
    # 5a. Question Paper Only (Separate Document)
    # -------------------------------------------------------------
    path_05a = os.path.join(output_dir, "05a_question_paper_only.pdf")
    c5a = canvas.Canvas(path_05a, pagesize=letter)
    c5a.setFont("Helvetica-Bold", 14)
    c5a.drawString(180, 750, "Physics Aptitude Test 2026")
    c5a.setFont("Helvetica", 10)
    c5a.drawString(50, 725, "Note: Answer key is issued in a separate official document.")

    c5a.setFont("Helvetica-Bold", 11)
    c5a.drawString(50, 680, "1. What is the SI unit of electrical resistance?")
    c5a.setFont("Helvetica", 10)
    c5a.drawString(70, 660, "A. Volt    B. Ampere    C. Ohm    D. Watt")

    c5a.setFont("Helvetica-Bold", 11)
    c5a.drawString(50, 610, "2. Which law states that for every action, there is an equal and opposite reaction?")
    c5a.setFont("Helvetica", 10)
    c5a.drawString(70, 590, "A. Newton's First Law    B. Newton's Second Law    C. Newton's Third Law    D. Law of Gravitation")

    c5a.showPage()
    c5a.save()
    print(f"Created: {path_05a}")

    # -------------------------------------------------------------
    # 5b. Separate Answer Key Document
    # -------------------------------------------------------------
    path_05b = os.path.join(output_dir, "05b_separate_answer_key.pdf")
    c5b = canvas.Canvas(path_05b, pagesize=letter)
    c5b.setFont("Helvetica-Bold", 14)
    c5b.drawString(160, 750, "Official Solution Key - Physics Aptitude Test 2026")
    c5b.setFont("Helvetica-Bold", 12)
    c5b.drawString(50, 690, "Answer Key:")
    c5b.setFont("Helvetica", 11)
    c5b.drawString(50, 660, "1: C")
    c5b.drawString(50, 630, "2: C")
    c5b.showPage()
    c5b.save()
    print(f"Created: {path_05b}")

    # -------------------------------------------------------------
    # 6. Invalid / Unsupported Text Document
    # -------------------------------------------------------------
    path_06 = os.path.join(output_dir, "06_invalid_format.txt")
    with open(path_06, "w", encoding="utf-8") as f:
        f.write("This is an unformatted plain text document that should be rejected by the upload validator.")
    print(f"Created: {path_06}")

    # -------------------------------------------------------------
    # 7. Corrupted / Malformed PDF
    # -------------------------------------------------------------
    path_07 = os.path.join(output_dir, "07_corrupted_file.pdf")
    with open(path_07, "wb") as f:
        f.write(b"CORRUPTED_NOT_A_REAL_PDF_HEADER_1234567890")
    print(f"Created: {path_07}")

    print("\nAll sample documents successfully generated!")


if __name__ == "__main__":
    create_sample_documents()
