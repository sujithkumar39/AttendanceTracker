import streamlit as st
import google.generativeai as genai
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
import os
import pandas as pd

# --- Configure Gemini API ---
load_dotenv(dotenv_path="keys.env")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Extract from Meeting Screenshot ---
def extract_attendance_from_image(image_file):
    model = genai.GenerativeModel("gemini-1.5-flash")
    image_bytes = image_file.getvalue()
    try:
        response = model.generate_content([
            "You are an attendance tracker. From this screenshot of a video call or meeting, extract the list of participants and whether their video is ON or OFF. Format response as:",
            "Name: [Name], Video: [ON/OFF]",
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

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

# --- Extract names from attendance list ---
def extract_names_from_file(file):
    try:
        if file.name.lower().endswith(".txt"):
            content = file.read().decode("utf-8")
            names = [line.strip() for line in content.splitlines() if line.strip()]
        else:  # Assume image
            model = genai.GenerativeModel("gemini-1.5-flash")
            image_bytes = file.getvalue()
            response = model.generate_content([
                "Extract only the names from this attendance list image. Just list the names line by line.",
                {"mime_type": "image/jpeg", "data": image_bytes}
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
        expected_names_set = set(name.lower() for name in expected_names)

        # Step 3: Compare
        extracted_names_set = set(name.lower() for name in attendance_df["Name"])
        present = sorted(set(expected_names_set & extracted_names_set))
        absent = sorted(set(expected_names_set - extracted_names_set))

        st.subheader("✅ Present Students")
        st.write(present if present else "None")

        st.subheader("❌ Absent Students")
        st.write(absent if absent else "None")

        st.subheader("📋 Extracted Attendance Data")
        st.dataframe(attendance_df, use_container_width=True)

        st.subheader("📝 Raw Output from Screenshot")
        st.code(raw_output)

        # Download buttons
        present_df = pd.DataFrame(present, columns=["Present"])
        absent_df = pd.DataFrame(absent, columns=["Absent"])

        st.download_button("Download Present List", present_df.to_csv(index=False), file_name="present.csv")
        st.download_button("Download Absent List", absent_df.to_csv(index=False), file_name="absent.csv")

    except UnidentifiedImageError:
        st.error("Invalid image. Please upload a valid JPG, JPEG, or PNG.")
    except Exception as e:
        st.error(f"Error: {e}")
   

