import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import os
import re
from utils import load_excel_data, get_receipt_image

# Set page configuration
st.set_page_config(
    page_title="ระบบตรวจสอบใบเสร็จจาก AI",
    page_icon="🧾",
    layout="wide"
)

# Application title
st.markdown("<h1 style='text-align: center;'>ระบบตรวจสอบใบเสร็จจาก AI</h1>", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
    
if 'verified_fields' not in st.session_state:
    st.session_state.verified_fields = {
        'tax_id': False,
        'receipt_number': False,
        'date': False,
        'time': False,
        'total_amount': False,
        'store_name': False
    }
    
if 'verification_stats' not in st.session_state:
    st.session_state.verification_stats = {
        'true1': 0,
        'true2': 0,
        'true3': 0,
        'true4': 0,
        'true5': 0,
        'true6': 0,
        'cancel': 0
    }

# Try to load data from Excel file
try:
    receipts_data = load_excel_data()
    file_options = [f"{i+1}. {file}" for i, file in enumerate(receipts_data['Source JSON File'])]
    
    # Dropdown for file selection
    with st.container():
        col_dropdown = st.columns([1, 3])
        with col_dropdown[0]:
            selected_file = st.selectbox(
                "ให้ทำ drop down ▼",
                options=file_options,
                index=st.session_state.current_index,
                key="file_selector"
            )
            
            # Update current index when dropdown selection changes
            selected_index = int(re.search(r'(\d+)\.', selected_file).group(1)) - 1
            if selected_index != st.session_state.current_index:
                st.session_state.current_index = selected_index
                st.session_state.verified_fields = {
                    'tax_id': False,
                    'receipt_number': False,
                    'date': False,
                    'time': False,
                    'total_amount': False,
                    'store_name': False
                }
                st.rerun()
    
    # Get the current receipt data
    current_receipt = receipts_data.iloc[st.session_state.current_index]
    json_filename = current_receipt['Source JSON File']
    img_filename = json_filename.replace('.json', '.jpg')
    
    # Main content area with two columns
    col1, col2, col3 = st.columns([4, 4, 2])
    
    # Column 1: Receipt Image
    with col1:
        st.markdown(
            """
            <div style='background-color: white; padding: 10px; border-radius: 10px; border: 1px solid #ddd;'>
                <h2 style='text-align: center;'>1</h2>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Display receipt image
        receipt_image = get_receipt_image(json_filename)
        if receipt_image:
            st.image(receipt_image, use_column_width=True)
        else:
            st.warning("ไม่พบรูปภาพใบเสร็จ")
        
        # Display image filename
        st.markdown(f"<p style='text-align: center;'>{img_filename}</p>", unsafe_allow_html=True)
    
    # Column 2: Extracted Data
    with col2:
        st.markdown(
            """
            <div style='background-color: white; padding: 10px; border-radius: 10px; border: 1px solid #ddd;'>
                <h2 style='text-align: center;'>2</h2>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Display extracted data with checkboxes
        tax_id = st.checkbox("Tax ID:", 
                           value=st.session_state.verified_fields['tax_id'], 
                           key='tax_id_checkbox')
        st.session_state.verified_fields['tax_id'] = tax_id
        
        receipt_number = st.checkbox("Receipt Number:", 
                                   value=st.session_state.verified_fields['receipt_number'], 
                                   key='receipt_number_checkbox')
        st.session_state.verified_fields['receipt_number'] = receipt_number
        
        date = st.checkbox("Date:", 
                         value=st.session_state.verified_fields['date'], 
                         key='date_checkbox')
        st.session_state.verified_fields['date'] = date
        
        time = st.checkbox("Time:", 
                         value=st.session_state.verified_fields['time'], 
                         key='time_checkbox')
        st.session_state.verified_fields['time'] = time
        
        total_amount = st.checkbox("Total Amount:", 
                                 value=st.session_state.verified_fields['total_amount'], 
                                 key='total_amount_checkbox')
        st.session_state.verified_fields['total_amount'] = total_amount
        
        store_name = st.checkbox("Store name:", 
                               value=st.session_state.verified_fields['store_name'], 
                               key='store_name_checkbox')
        st.session_state.verified_fields['store_name'] = store_name
        
        # Display JSON filename
        st.markdown(f"<p style='text-align: center;'>{json_filename}</p>", unsafe_allow_html=True)
    
    # Column 3: Verification Summary
    with col3:
        st.markdown(
            """
            <div style='background-color: #FF4B4B; color: white; padding: 10px; border-radius: 10px;'>
                <p style='margin: 5px;'>true6:</p>
                <p style='margin: 5px;'>true5:</p>
                <p style='margin: 5px;'>true4:</p>
                <p style='margin: 5px;'>true3:</p>
                <p style='margin: 5px;'>true2:</p>
                <p style='margin: 5px;'>true1:</p>
                <p style='margin: 5px;'>cancel:</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Verification buttons
    col_buttons = st.columns([4, 2, 2, 2])
    
    with col_buttons[1]:
        if st.button("Yes", key="yes_button", use_container_width=True, 
                    type="primary", help="Confirm verification"):
            # Calculate number of checked items
            checked_count = sum(1 for field, checked in st.session_state.verified_fields.items() if checked)
            
            # Update verification stats
            if checked_count > 0:
                stat_key = f'true{checked_count}'
                if stat_key in st.session_state.verification_stats:
                    st.session_state.verification_stats[stat_key] += 1
            
            # Reset verification fields and move to next receipt
            st.session_state.verified_fields = {field: False for field in st.session_state.verified_fields}
            st.session_state.current_index = (st.session_state.current_index + 1) % len(receipts_data)
            st.rerun()
    
    with col_buttons[2]:
        if st.button("cancel", key="cancel_button", use_container_width=True, 
                    help="Cancel verification"):
            # Update cancel stats
            st.session_state.verification_stats['cancel'] += 1
            
            # Reset verification fields and move to next receipt
            st.session_state.verified_fields = {field: False for field in st.session_state.verified_fields}
            st.session_state.current_index = (st.session_state.current_index + 1) % len(receipts_data)
            st.rerun()

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}")
    st.markdown("""
    ### วิธีการใช้งาน:
    1. อัปโหลดไฟล์ Excel ที่มีข้อมูล OCR (data_ocr_extract.xlsx)
    2. ตรวจสอบข้อมูลที่ได้จากการสกัดด้วย AI
    3. ทำเครื่องหมายที่ช่องที่ข้อมูลถูกต้อง
    4. กด "Yes" เพื่อยืนยันหรือ "cancel" เพื่อยกเลิก
    """)
