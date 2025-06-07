import streamlit as st
import google.generativeai as genai
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
import os
import pandas as pd

# --- Configure Gemini API ---
load_dotenv(dotenv_path="keys.env")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_attendance_from_image(image_file):
    model = genai.GenerativeModel("gemini-1.5-flash")
    image_bytes = image_file.getvalue()

    try:
        response = model.generate_content([
            "You are an attendance tracker. From this screenshot of a video call or meeting, extract the list of participants and whether their video is ON or OFF. Format the response clearly as:",
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

# --- Streamlit UI ---
st.set_page_config(page_title="Attendance Tracker", layout="centered")
st.title("📸 Attendance Tracker from Screenshot")
st.markdown("Upload a screenshot from a meeting. The AI will extract participant names and check if their video is ON or OFF.")

uploaded_image = st.file_uploader("Upload Meeting Screenshot (JPG, JPEG, or PNG)", type=["jpg", "jpeg", "png"])

if uploaded_image:
    try:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Screenshot", use_container_width=True)

        with st.spinner("Analyzing screenshot..."):
            raw_output = extract_attendance_from_image(uploaded_image)
            attendance_df = parse_attendance_data(raw_output)

        st.subheader("📋 Attendance Data")
        st.dataframe(attendance_df, use_container_width=True)

        st.subheader("🔍 Raw Extracted Info (for debugging)")
        st.code(raw_output)

    except UnidentifiedImageError:
        st.error("Invalid image. Please upload a valid JPG, JPEG, or PNG.")
    except Exception as e:
        st.error(f"Error processing image: {e}")

