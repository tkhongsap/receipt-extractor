import streamlit as st
import pandas as pd
import re
import os
from utils import load_excel_data, get_receipt_image
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="ระบบตรวจสอบใบเสร็จจาก AI (OpenAI Azure)",
    page_icon="🧾",
    layout="wide"
)

# Custom CSS for portrait image display, full dropdown text และการซูมภาพ
st.markdown("""
<style>
    /* Image display as portrait - ไม่จำกัดความสูงและความกว้างเพื่อให้ใช้ความละเอียดต้นฉบับ */
    div.stImage > img {
        max-height: none !important;
        max-width: 100% !important;
        width: auto !important;
        margin: 0 auto !important;
        display: block !important;
        transform: rotate(0deg) !important;
    }
    
    /* Container for image with fixed height */
    div[data-testid="column"]:first-child > div {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    /* Checkbox styling for accessibility */
    .stCheckbox label {
        min-width: 50px !important;
    }
    
    /* Make dropdown wider to show full text */
    div[data-testid="stSelectbox"] {
        width: 100%;
        min-width: 300px;
    }
    
    /* Prevent dropdown text from being truncated */
    div[data-testid="stSelectbox"] > div > div > div {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: 100% !important;
    }
    
    /* Fix for dropdown options */
    div[role="listbox"] div[role="option"] {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        line-height: 1.4 !important;
        padding: 8px !important;
    }
    
    /* ปรับแต่ง expander สำหรับการซูมภาพ */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #FF4B4B;
    }
    
    /* ทำให้ภาพในโหมดซูมมีขนาดใหญ่ */
    div[data-testid="stExpander"] div.stImage > img {
        max-width: 100% !important;
        max-height: none !important;
        cursor: zoom-in;
    }
    
    /* ทำให้เส้นใต้ของชื่อบางลง */
    .stApp header {
        border-bottom-width: 1px !important;
        border-bottom-color: rgba(38, 39, 48, 0.1) !important;
    }
    
    /* ปรับแต่งเส้นใต้ของหัวข้อต่างๆ ให้บางลง */
    h1, h2, h3, h4, h5, h6 {
        border-bottom: 1px solid rgba(38, 39, 48, 0.1) !important;
        padding-bottom: 0.3em;
    }
</style>
""", unsafe_allow_html=True)

# Application title
st.markdown("<h1 style='text-align: center; border-bottom: 1px solid rgba(38, 39, 48, 0.1); padding-bottom: 0.3em;'>ระบบตรวจสอบใบเสร็จจาก AI (OpenAI Azure)</h1>", unsafe_allow_html=True)

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

# Keep track of verified receipts
if 'verified_receipts' not in st.session_state:
    st.session_state.verified_receipts = set()

# Try to load data from Excel file
try:
    # Load all receipts data
    receipts_data = load_excel_data()
    
    # Filter out verified receipts from the dropdown options
    available_receipts = receipts_data.copy()
    if len(st.session_state.verified_receipts) > 0:
        available_receipts = receipts_data[~receipts_data['Source JSON File'].isin(st.session_state.verified_receipts)]
    
    # Reset index if no more receipts to verify or current index is out of range
    if len(available_receipts) == 0:
        # All receipts have been verified
        st.info("ดำเนินการตรวจสอบใบเสร็จทั้งหมดเรียบร้อยแล้ว กดปุ่ม 'เริ่มต้นใหม่' เพื่อตรวจสอบอีกครั้ง")
        # Use full set for display
        available_receipts = receipts_data
        if st.session_state.current_index >= len(receipts_data):
            st.session_state.current_index = 0
    elif st.session_state.current_index >= len(available_receipts):
        st.session_state.current_index = 0
    
    # Create file options for dropdown - show full filename
    file_options = []
    for i, file in enumerate(available_receipts['Source JSON File']):
        # เพิ่มหมายเลขและใช้ชื่อไฟล์เต็มโดยไม่ตัด
        file_options.append(f"{i+1}. {file}")
    
    # Dropdown for file selection
    with st.container():
        st.markdown(
            """
            <div style='background-color: #FF4B4B; color: white; padding: 10px; border-radius: 10px;'>
            """, 
            unsafe_allow_html=True
        )
        # แก้ไขสัดส่วนของคอลัมน์ให้กว้างขึ้นเพื่อป้องกันการทับซ้อน
        col_dropdown = st.columns([2, 1])
        with col_dropdown[0]:
            if len(file_options) > 0:
                selected_file = st.selectbox(
                    "เลือกใบเสร็จที่ต้องการตรวจสอบ",
                    options=file_options,
                    index=min(st.session_state.current_index, len(file_options)-1),
                    key="file_selector",
                    label_visibility="collapsed"
                )
                
                # Update current index when dropdown selection changes
                selected_match = re.search(r'(\d+)\.', selected_file)
                if selected_match:
                    # แปลงเป็น int และเก็บเป็น Python int (ไม่ใช่ numpy.int64)
                    selected_index = int(selected_match.group(1)) - 1
                    if selected_index != st.session_state.current_index:
                        st.session_state.current_index = int(selected_index)  # ใช้ int() เพื่อแปลงเป็น Python int
                        st.session_state.verified_fields = {
                            'tax_id': False,
                            'receipt_number': False,
                            'date': False,
                            'time': False,
                            'total_amount': False,
                            'store_name': False
                        }
                        st.rerun()
            else:
                st.write("ไม่มีใบเสร็จที่ยังไม่ได้ตรวจสอบ")
        
        # Add reset button to dropdown area
        with col_dropdown[1]:
            if st.button("เริ่มต้นใหม่", key="reset_button", help="เคลียร์ผลลัพธ์ทั้งหมดและเริ่มตรวจสอบใหม่"):
                # Reset all stats and verification info
                st.session_state.verification_stats = {
                    'true6': 0, 'true5': 0, 'true4': 0, 'true3': 0, 'true2': 0, 'true1': 0, 'cancel': 0
                }
                st.session_state.verified_receipts = set()
                st.session_state.current_index = 0
                st.session_state.verified_fields = {field: False for field in st.session_state.verified_fields}
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Get the current receipt data from available receipts
    if len(available_receipts) > 0:
        # แปลงเป็น Python int เพื่อป้องกันปัญหา numpy.int64
        current_index = int(min(st.session_state.current_index, len(available_receipts)-1))
        current_receipt = available_receipts.iloc[current_index]
        json_filename = current_receipt['Source JSON File']
        img_filename = json_filename.replace('.json', '.jpg')
        
        # Main content area with three columns
        col1, col2, col3 = st.columns([4, 4, 2])
        
        # Column 1: Receipt Image
        with col1:
            # Create a container with border and big number 1
            st.markdown(
                """
                <div style='border: 1px solid #ddd; border-radius: 10px; padding: 10px; position: relative;'>
                    <div style='font-size: 60px; font-weight: bold; position: absolute; top: 10px; right: 20px; color: black;'>
                        1
                    </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Display receipt image in portrait orientation
            receipt_image = get_receipt_image(json_filename)
            if receipt_image:
                # Resize image to be taller than it is wide (force portrait mode)
                width, height = receipt_image.size
                if width > height:
                    # This is a landscape image, rotate it to portrait
                    # Use 270 degrees instead of 90 to avoid upside-down images
                    receipt_image = receipt_image.rotate(270, expand=True)
                
                # เพิ่มเครื่องมือซูมภาพด้วย st.expander
                with st.expander("คลิกที่นี่เพื่อซูมภาพ", expanded=False):
                    # แสดงภาพขนาดใหญ่ในความละเอียดเต็มเมื่อคลิกที่ expander
                    st.image(receipt_image, use_container_width=True, caption="คลิกขวาที่ภาพและเลือก 'Open image in new tab' เพื่อดูภาพขนาดเต็ม")
                
                # แสดงภาพในหน้าหลักด้วยความละเอียดต้นฉบับ ไม่กำหนดความกว้าง
                st.image(receipt_image, use_container_width=False)
            else:
                st.warning("ไม่พบรูปภาพใบเสร็จ")
            
            # Display image filename
            st.markdown(f"<p style='text-align: center;'>{img_filename}</p>", unsafe_allow_html=True)
            
            # Close the container div
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Column 2: Extracted Data with Checkmarks
        with col2:
            # Create a container with border and big number 2
            st.markdown(
                """
                <div style='border: 1px solid #ddd; border-radius: 10px; padding: 10px; position: relative;'>
                    <div style='font-size: 60px; font-weight: bold; position: absolute; top: 10px; right: 20px; color: black;'>
                        2
                    </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Display extracted data with checkboxes
            
            # Tax ID
            tax_id_value = current_receipt['Tax ID'] if pd.notna(current_receipt['Tax ID']) else "ไม่พบข้อมูล"
            col_tax_id = st.columns([0.1, 0.9])
            with col_tax_id[0]:
                tax_id = st.checkbox("ถูกต้อง", value=st.session_state.verified_fields['tax_id'], key='tax_id_checkbox', label_visibility="collapsed")
                st.session_state.verified_fields['tax_id'] = tax_id
            with col_tax_id[1]:
                st.markdown(f"**Tax ID:** {tax_id_value}")
                
            # Receipt Number
            receipt_number_value = current_receipt['Receipt Number'] if pd.notna(current_receipt['Receipt Number']) else "ไม่พบข้อมูล"
            col_receipt = st.columns([0.1, 0.9])
            with col_receipt[0]:
                receipt_number = st.checkbox("ถูกต้อง", value=st.session_state.verified_fields['receipt_number'], key='receipt_number_checkbox', label_visibility="collapsed")
                st.session_state.verified_fields['receipt_number'] = receipt_number
            with col_receipt[1]:
                st.markdown(f"**Receipt Number:** {receipt_number_value}")
                
            # Date
            date_value = "ไม่พบข้อมูล"
            if pd.notna(current_receipt['Date']):
                try:
                    # Check if the date is already a string
                    if isinstance(current_receipt['Date'], str):
                        date_value = current_receipt['Date']
                    else:
                        # Try to format as date if it's a datetime object
                        date_value = current_receipt['Date'].strftime('%Y-%m-%d')
                except:
                    # If any error occurs, use the original value as is
                    date_value = str(current_receipt['Date'])
            
            col_date = st.columns([0.1, 0.9])
            with col_date[0]:
                date = st.checkbox("ถูกต้อง", value=st.session_state.verified_fields['date'], key='date_checkbox', label_visibility="collapsed")
                st.session_state.verified_fields['date'] = date
            with col_date[1]:
                st.markdown(f"**Date:** {date_value}")
                
            # Time
            time_value = current_receipt['Time'] if pd.notna(current_receipt['Time']) else "ไม่พบข้อมูล"
            col_time = st.columns([0.1, 0.9])
            with col_time[0]:
                time = st.checkbox("ถูกต้อง", value=st.session_state.verified_fields['time'], key='time_checkbox', label_visibility="collapsed")
                st.session_state.verified_fields['time'] = time
            with col_time[1]:
                st.markdown(f"**Time:** {time_value}")
                
            # Total Amount
            total_amount_value = "ไม่พบข้อมูล"
            if pd.notna(current_receipt['Total Amount']):
                try:
                    total_amount_value = f"{float(current_receipt['Total Amount']):.2f}"
                except:
                    total_amount_value = str(current_receipt['Total Amount'])
                    
            col_total = st.columns([0.1, 0.9])
            with col_total[0]:
                total_amount = st.checkbox("ถูกต้อง", value=st.session_state.verified_fields['total_amount'], key='total_amount_checkbox', label_visibility="collapsed")
                st.session_state.verified_fields['total_amount'] = total_amount
            with col_total[1]:
                st.markdown(f"**Total Amount:** {total_amount_value}")
                
            # Store name
            store_name_value = current_receipt['Store name'] if pd.notna(current_receipt['Store name']) else "ไม่พบข้อมูล"
            col_store = st.columns([0.1, 0.9])
            with col_store[0]:
                store_name = st.checkbox("ถูกต้อง", value=st.session_state.verified_fields['store_name'], key='store_name_checkbox', label_visibility="collapsed")
                st.session_state.verified_fields['store_name'] = store_name
            with col_store[1]:
                st.markdown(f"**Store name:** {store_name_value}")
            
            # Display JSON filename at the bottom
            st.markdown(f"<p style='text-align: center; margin-top: 20px;'>{json_filename}</p>", unsafe_allow_html=True)
            
            # Close the container div
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Column 3: Verification Summary
        with col3:
            # Count the total number of verified items in each category
            st.markdown(
                f"""
                <div style='background-color: #FF4B4B; color: white; padding: 15px; border-radius: 10px;'>
                    <p style='margin: 5px;'><b>true6:</b> {st.session_state.verification_stats['true6']}</p>
                    <p style='margin: 5px;'><b>true5:</b> {st.session_state.verification_stats['true5']}</p>
                    <p style='margin: 5px;'><b>true4:</b> {st.session_state.verification_stats['true4']}</p>
                    <p style='margin: 5px;'><b>true3:</b> {st.session_state.verification_stats['true3']}</p>
                    <p style='margin: 5px;'><b>true2:</b> {st.session_state.verification_stats['true2']}</p>
                    <p style='margin: 5px;'><b>true1:</b> {st.session_state.verification_stats['true1']}</p>
                    <p style='margin: 5px;'><b>cancel:</b> {st.session_state.verification_stats['cancel']}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # Verification buttons
        st.markdown("<br>", unsafe_allow_html=True)  # Add some space
        col_buttons = st.columns([5, 2, 2, 1])
        
        with col_buttons[1]:
            if st.button("Yes", key="yes_button", use_container_width=True, 
                        type="primary", help="ยืนยันการตรวจสอบ"):
                # Calculate number of checked items
                checked_count = sum(1 for field, checked in st.session_state.verified_fields.items() if checked)
                
                # Update verification stats
                if checked_count > 0:
                    stat_key = f'true{checked_count}'
                    if stat_key in st.session_state.verification_stats:
                        st.session_state.verification_stats[stat_key] += 1
                
                # Add this receipt to verified list
                st.session_state.verified_receipts.add(json_filename)
                
                # Reset verification fields
                st.session_state.verified_fields = {field: False for field in st.session_state.verified_fields}
                
                # Find next unverified receipt and update index
                if len(st.session_state.verified_receipts) < len(receipts_data):
                    unverified_receipts = receipts_data[~receipts_data['Source JSON File'].isin(st.session_state.verified_receipts)]
                    if len(unverified_receipts) > 0:
                        # Get the index of the first unverified receipt from the original dataframe
                        next_receipt = unverified_receipts.iloc[0]['Source JSON File']
                        next_index = receipts_data[receipts_data['Source JSON File'] == next_receipt].index[0]
                        # แปลงเป็น Python int เพื่อป้องกันปัญหา numpy.int64
                        st.session_state.current_index = int(next_index)
                
                st.rerun()
        
        with col_buttons[2]:
            if st.button("cancel", key="cancel_button", use_container_width=True, 
                        help="ยกเลิกการตรวจสอบ"):
                # Update cancel stats
                st.session_state.verification_stats['cancel'] += 1
                
                # Add this receipt to verified list (even though it was canceled)
                st.session_state.verified_receipts.add(json_filename)
                
                # Reset verification fields
                st.session_state.verified_fields = {field: False for field in st.session_state.verified_fields}
                
                # Find next unverified receipt and update index
                if len(st.session_state.verified_receipts) < len(receipts_data):
                    unverified_receipts = receipts_data[~receipts_data['Source JSON File'].isin(st.session_state.verified_receipts)]
                    if len(unverified_receipts) > 0:
                        # Get the index of the first unverified receipt from the original dataframe
                        next_receipt = unverified_receipts.iloc[0]['Source JSON File']
                        next_index = receipts_data[receipts_data['Source JSON File'] == next_receipt].index[0]
                        # แปลงเป็น Python int เพื่อป้องกันปัญหา numpy.int64
                        st.session_state.current_index = int(next_index)
                
                st.rerun()

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}")
    st.markdown("""
    ### วิธีการใช้งาน:
    1. อัปโหลดไฟล์ Excel ที่มีข้อมูล OCR (data_ocr_extract.xlsx)
    2. ตรวจสอบข้อมูลที่ได้จากการสกัดด้วย AI
    3. ทำเครื่องหมายที่ช่องที่ข้อมูลถูกต้อง
    4. กด "Yes" เพื่อยืนยันหรือ "cancel" เพื่อยกเลิก
    5. กด "เริ่มต้นใหม่" เพื่อเคลียร์ผลลัพธ์และเริ่มตรวจสอบใหม่
    """)