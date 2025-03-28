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
    # Check if the Excel file exists in the current directory
    excel_path = "data_ocr_extract.xlsx"
    
    # For demonstration, if file doesn't exist, we'll return some sample data
    if not os.path.exists(excel_path):
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
                '1738659029705399729504443827439.json',
                '1738659029705399729504443827440.json',
                '1738659029705399729504443827441.json'
            ]
        }
        return pd.DataFrame(sample_data)
    
    # If file exists, load it
    try:
        df = pd.read_excel(excel_path)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ Excel: {str(e)}")
        raise e

def get_receipt_image(json_filename):
    """
    Get receipt image based on JSON filename.
    In a real implementation, this would fetch from SharePoint.
    
    Args:
        json_filename (str): The JSON filename from the Excel data
    
    Returns:
        PIL.Image or None: The receipt image if found, None otherwise
    """
    # Convert JSON filename to image filename
    img_filename = json_filename.replace('.json', '.jpg')
    
    # Check if the image exists locally (for testing)
    local_path = os.path.join("receipts", img_filename)
    if os.path.exists(local_path):
        return Image.open(local_path)
    
    # Allow user to upload image for testing
    st.write(f"รูปภาพใบเสร็จไม่พบในระบบ คุณสามารถอัปโหลดรูปภาพได้ที่นี่:")
    uploaded_image = st.file_uploader(f"อัปโหลดรูปภาพสำหรับ {img_filename}", type=["jpg", "jpeg", "png"])
    
    if uploaded_image is not None:
        return Image.open(uploaded_image)
    
    # In real implementation, would fetch from SharePoint using the provided link
    # SharePoint link would be implemented here if we had access credentials
    
    # For demonstration purposes (using a placeholder image):
    placeholder_image = Image.new('RGB', (300, 400), color=(240, 240, 240))
    return placeholder_image
