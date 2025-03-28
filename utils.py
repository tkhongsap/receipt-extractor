import pandas as pd
import os
import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import tempfile

def load_excel_data():
    """
    Load data from Excel file or use sample data if file is not available.
    
    Returns:
        pandas.DataFrame: DataFrame containing receipt data
    """
    # Check if the Excel file exists in the data directory
    excel_path = "data/data_ocr_extract.xlsx"
    
    # If file exists, load it
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            return df
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ Excel: {str(e)}")
            raise e
    
    # If not found in data directory, check the current directory
    excel_path = "data_ocr_extract.xlsx"
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            return df
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ Excel: {str(e)}")
            raise e
            
    # If file doesn't exist in either location, show upload option
    st.warning("ไม่พบไฟล์ Excel (data_ocr_extract.xlsx) ในระบบ กรุณาอัปโหลดไฟล์ก่อนใช้งาน")
    
    # Allow user to upload Excel file
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ Excel (data_ocr_extract.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name
        
        # Load the data from the temporary file
        try:
            df = pd.read_excel(temp_path)
            os.unlink(temp_path)  # Delete the temporary file
            return df
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ Excel: {str(e)}")
            os.unlink(temp_path)  # Delete the temporary file
            raise e
    
    # If no file is uploaded, use sample data
    sample_data = {
        'Source JSON File': [
            '17386590297053997295044438274399 - Victor Lee.json',
            '17386590966462230082736051626241 - Victor Lee.json',
            '17387186556135444632046881269223 - Victor Lee.json'
        ],
        'Tax ID': ['105560000000', '105558000000', '107536000000'],
        'Receipt Number': ['10344000000000000', '001-3 [006240]', None],
        'Date': ['2025-04-02', '2025-02-04', '2025-02-03'],
        'Time': ['14:04:32', '12:16:00', None],
        'Total Amount': [None, 494.34, 535.00],
        'Store name': ['Brewing Happiness Co.,Ltd.', 'Tonkatsu Wako One Bangkok', 'BIGC MARKET THE ONE BANGKOK']
    }
    return pd.DataFrame(sample_data)

def get_receipt_image(json_filename):
    """
    Get receipt image based on JSON filename from local storage.
    
    Args:
        json_filename (str): The JSON filename from the Excel data
    
    Returns:
        PIL.Image or None: The receipt image if found, None otherwise
    """
    # Convert JSON filename to image filename
    img_filename = json_filename.replace('.json', '.jpg')
    
    # First check in the data/receipts_raw directory
    receipts_raw_dir = "data/receipts_raw"
    if os.path.exists(receipts_raw_dir):
        raw_image_path = os.path.join(receipts_raw_dir, img_filename)
        if os.path.exists(raw_image_path):
            try:
                return Image.open(raw_image_path)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการเปิดรูปภาพจาก receipts_raw: {str(e)}")
    
    # Check if we already have a receipts directory and the image exists locally as fallback
    receipts_dir = "receipts"
    if not os.path.exists(receipts_dir):
        os.makedirs(receipts_dir)
        
    local_path = os.path.join(receipts_dir, img_filename)
    if os.path.exists(local_path):
        try:
            return Image.open(local_path)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการเปิดรูปภาพจาก receipts: {str(e)}")
    
    # If the exact filename doesn't exist, try partial matching for the ID part
    # Extract base filename without extension
    # Example: '17386590297053997295044438274399 - Victor Lee.json' -> '17386590297053997295044438274399'
    base_filename = json_filename.split(' - ')[0] if ' - ' in json_filename else json_filename.split('.')[0]
    
    # Try to find a matching file in receipts_raw
    if os.path.exists(receipts_raw_dir):
        for filename in os.listdir(receipts_raw_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')) and base_filename in filename:
                try:
                    image_path = os.path.join(receipts_raw_dir, filename)
                    receipt_image = Image.open(image_path)
                    
                    # Save a copy to the standard receipts directory for future use
                    receipt_image.save(local_path)
                    
                    return receipt_image
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการเปิดรูปภาพที่ตรงกัน: {str(e)}")
    
    # Allow user to upload image manually as a last resort
    st.warning(f"ไม่พบรูปภาพใบเสร็จสำหรับ {img_filename}")
    st.write("คุณสามารถอัปโหลดรูปภาพได้ที่นี่:")
    uploaded_image = st.file_uploader(f"อัปโหลดรูปภาพสำหรับ {img_filename}", type=["jpg", "jpeg", "png"])
    
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        # Save uploaded image for future use
        image.save(local_path)
        return image
    
    # Create a simple receipt placeholder if all else fails
    width, height = 600, 800
    placeholder_image = Image.new('RGB', (width, height), color=(245, 245, 245))
    
    # Add text to the placeholder image
    import PIL.ImageDraw
    import PIL.ImageFont
    draw = PIL.ImageDraw.Draw(placeholder_image)
    try:
        # Try to use a system font
        font = PIL.ImageFont.truetype("Arial", 20)
    except:
        # Fall back to default
        font = PIL.ImageFont.load_default()
        
    draw.text((width/2-150, height/2-50), f"ไม่พบรูปภาพใบเสร็จ", fill=(0, 0, 0), font=font)
    draw.text((width/2-150, height/2), f"ID: {base_filename}", fill=(0, 0, 0), font=font)
    
    # Save the placeholder image for future use
    placeholder_image.save(local_path)
    return placeholder_image
