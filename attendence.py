import streamlit as st
import google.generativeai as genai
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
import os
import pandas as pd
import imghdr

# --- Configure Gemini API ---
load_dotenv(dotenv_path="keys.env")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Helper to detect mime type ---
def get_mime_type(file):
    img_type = imghdr.what(None, file.getvalue())
    return f"image/{img_type}" if img_type else "image/jpeg"

# --- Extract from Meeting Screenshot ---
def extract_attendance_from_image(image_file):
    model = genai.GenerativeModel("gemini-1.5-flash")
    image_bytes = image_file.getvalue()
    mime_type = get_mime_type(image_file)
    try:
        response = model.generate_content([
            "You are an attendance tracker. From this screenshot of a video call or meeting, extract the list of participants and whether their video is ON or OFF. Format response as:",
            "Name: [Name], Video: [ON/OFF]",
            {"mime_type": mime_type, "data": image_bytes}
        ])
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# --- Parse output to dataframe ---
def parse_attendance_data(raw_text):
    data = []
    lines = raw_text.splitlines()
    for line in lines:
        if "Name:" in line and "Video:" in line:
            try:
                name_part = line.split("Name:")[1].split(",")[0].strip()
                video_part = line.split("Video:")[1].strip().upper()
                if video_part not in ["ON", "OFF"]:
                    video_part = "UNKNOWN"
                data.append({"Name": name_part, "Video Status": video_part})
            except:
                continue
    return pd.DataFrame(data)

# --- Extract names from attendance list file ---
def extract_names_from_file(file):
    try:
        if file.name.lower().endswith(".txt"):
            content = file.read().decode("utf-8")
            names = [line.strip() for line in content.splitlines() if line.strip()]
        else:  # Assume image
            model = genai.GenerativeModel("gemini-1.5-flash")
            image_bytes = file.getvalue()
            mime_type = get_mime_type(file)
            response = model.generate_content([
                "Extract only the names from this attendance list image. Just list the names line by line.",
                {"mime_type": mime_type, "data": image_bytes}
            ])
            names = [line.strip() for line in response.text.splitlines() if line.strip()]
        return names
    except Exception as e:
        st.error(f"Error extracting names from attendance list: {e}")
        return []

# --- Streamlit UI ---
st.set_page_config(page_title="Attendance Tracker", layout="centered")
st.title("📸 Attendance Tracker from Screenshot + List Comparison")

st.markdown("### Step 1: Upload Meeting Screenshot")
screenshot_file = st.file_uploader("Upload meeting screenshot (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"])

st.markdown("### Step 2: Upload Attendance List (TXT or Image)")
attendance_list_file = st.file_uploader("Upload attendance list (TXT or Image)", type=["txt", "jpg", "jpeg", "png"])

if screenshot_file and attendance_list_file:
    try:
        # Step 1: Analyze screenshot
        st.image(screenshot_file, caption="Meeting Screenshot", use_container_width=True)
        with st.spinner("Analyzing screenshot..."):
            raw_output = extract_attendance_from_image(screenshot_file)
            attendance_df = parse_attendance_data(raw_output)

        # Step 2: Extract expected names
        expected_names = extract_names_from_file(attendance_list_file)
        if not expected_names:
            st.warning("No names found in the attendance list.")
            st.stop()

        extracted_names = [str(name).strip() for name in attendance_df["Name"]]

        # Step 3: Partial matching logic
        present = []
        absent = []

        for expected_name in expected_names:
            expected_parts = expected_name.lower().split()
            matched = False
            for extracted_name in extracted_names:
                extracted_lower = extracted_name.lower()
                if any(part in extracted_lower for part in expected_parts):
                    matched = True
                    break
            if matched:
                present.append(expected_name)
            else:
                absent.append(expected_name)

        # Step 4: Display results
        st.subheader("✅ Present Students")
        st.write(present if present else "None")

        st.subheader("❌ Absent Students")
        st.write(absent if absent else "None")

        st.subheader("📋 Extracted Attendance Data")
        st.dataframe(attendance_df, use_container_width=True)

        st.subheader("📝 Raw Output from Screenshot")
        st.code(raw_output)

        # Step 5: Download buttons
        present_df = pd.DataFrame(present, columns=["Present"])
        absent_df = pd.DataFrame(absent, columns=["Absent"])
        st.download_button("Download Present List", present_df.to_csv(index=False), file_name="present.csv")
        st.download_button("Download Absent List", absent_df.to_csv(index=False), file_name="absent.csv")
        st.download_button("Download Full Attendance Data", attendance_df.to_csv(index=False), file_name="full_attendance.csv")

    except UnidentifiedImageError:
        st.error("Invalid image. Please upload a valid JPG, JPEG, or PNG.")
    except Exception as e:
        st.error(f"Error: {e}")
