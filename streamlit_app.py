import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import io
import openai

pd.options.display.float_format = "{:,.2f}".format
st.set_page_config(layout="wide")

# Function to load custom CSS
def load_css():
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Load the custom CSS
load_css()

def extract_data_from_pdf(byte_data, bank_name):
    """
    Extracts all text from a PDF file using pdfplumber.
    Args:
    byte_data (bytes): Byte data from the uploaded PDF file.
    Returns:
    str: Extracted text from the PDF.
    """
    extracted_text = ""
    with pdfplumber.open(io.BytesIO(byte_data)) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"  # Extract and add new line
    return extracted_text
    



def process_files(uploaded_files):
    final_dataframe = pd.DataFrame()
    for uploaded_file in uploaded_files:

        if uploaded_file is not None:
            bank_name = 'GenericBank'  # Assuming bank name can be inferred or is generic
            byte_data = uploaded_file.getvalue()  # Get byte data from uploaded file
            edo_de_cuenta = extract_data_from_pdf(byte_data, bank_name)
            edo_de_cuenta_list = edo_de_cuenta.split("\n")
            print("1) Lectura de Estado de Cuenta")
            
            #Identificar los Movimientos de Estado de Cuenta
            movimientos_list = [item for item in edo_de_cuenta_list if '$' in item]
            
            Movements_list = []
            for item in movimientos_list:
                if item and item[0].isdigit():  # Check if the first character is a digit
                    Movements_list.append(item)
            print("2) Identificar los Movimientos de Estado de Cuenta")
            
            
            #Identificar Movimientos unicos o diferidos en Estado de Cuenta
            movimientos_unicos_list = []
            movimientos_diferidos_list = []
            
            for item in Movements_list:
                dollar_count = item.count('$') 
                if dollar_count == 1:
                    movimientos_unicos_list.append(item)
                elif dollar_count > 1:
                    movimientos_diferidos_list.append(item)
                    
            print("3) Identificar Movimientos unicos o diferidos en Estado de Cuenta")
            
            
            #Extraer Fecha, Concepto y Monto de cada registro
            fecha = []
            concepto = []
            monto = []
            for i in movimientos_unicos_list:
                fecha.append(i[:5])
                concepto.append(i[6:].split("$")[0])
                monto.append(i.split("$")[1].replace(",",""))
            
            for i in movimientos_diferidos_list:
                fecha.append(i[:5])
                concepto.append(i[6:].split("$")[0])
                monto.append(i.split("$")[3].replace(",",""))
                
            print("4) Extraer Fecha, Concepto y Monto de cada registro")
            
            
            #Cambiar Orden de Signo en Montos Negativos
            monto_con_signo = []
            for m in monto:
                if m[-1] == "-":
                    monto_con_signo.append("-"+m[:-1])
                else:
                    monto_con_signo.append(m)
            
            #DataFrame de Estado de Cuenta
            estado_de_cuenta_movimientos_df = pd.DataFrame({'Fecha' : fecha,
                                            'Concepto' : concepto,
                                            'Monto' : monto_con_signo }, 
                                            columns=['Fecha','Concepto', 'Monto'])
            
            estado_de_cuenta_movimientos_df["Monto"] = estado_de_cuenta_movimientos_df["Monto"].astype(float)
            estado_de_cuenta_movimientos_df["Fecha"] =  pd.to_datetime(estado_de_cuenta_movimientos_df["Fecha"]+"/2024", format='%d/%m/%Y')
            estado_de_cuenta_movimientos_df = estado_de_cuenta_movimientos_df.sort_values(by = ["Fecha","Concepto"])
            
            print("5) DataFrame de Estado de Cuenta")
            
            
            #Clasificar por Comercio
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            
            comercio_list = []
                
            for word in list(estado_de_cuenta_movimientos_df["Concepto"]):
                def classify_word(word):
                    prompt_for_classification = f"Identifica el comercio al que pudiera pertenecer este concepto de un estado de cuenta: {word}. Un ejemplo pudiera ser 'STRIPE *UBER TRIP CIUDAD DE MEX MX UPM' y Uber, u 'OXXO DEL CARMEN MONTERREY NL MX CCO' y OXXO. No incluyas explicación, ni desarrollo, ni justificación; sólamente el comercio. Si es que no hay suficiente información para clasificar, pon '0'."
                    response = openai.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt_for_classification}
                        ]
                        
                    )
                    classification = response.choices[0].message.content.strip()
                    return classification
                comercio = classify_word(word)
                comercio_list.append(comercio)
            
            estado_de_cuenta_movimientos_df["Comercio"] = comercio_list
            print("6) Clasificar por Comercio")
            
            
            #Cambiar Signo (TDC cambian de Positivo a Negativo)
            estado_de_cuenta_movimientos_df["Monto"] = -1 * estado_de_cuenta_movimientos_df["Monto"]
            
            #Calcular Acumulado
            print("7) Tabla Final")
            
            # Concatenate the DataFrame into the final DataFrame
            final_dataframe = pd.concat([final_dataframe, estado_de_cuenta_movimientos_df], ignore_index=True)
        
            final_dataframe = final_dataframe.sort_values(by = ["Fecha","Concepto"])
            final_dataframe["Monto Acumulado"] = final_dataframe["Monto"].cumsum()
            final_dataframe = final_dataframe[["Fecha", "Concepto", "Comercio", "Monto", "Monto Acumulado"]]
            final_dataframe["Comercio"] = final_dataframe["Comercio"].str.title()

    return final_dataframe



def load_navbar(user_name):
    navbar_html = f"""
    <style>
        body {{
            margin: 0;
            font-family: 'Roboto', sans-serif;
        }}
        .navbar {{
            width: 100%;
            background-color: #EEF2F8; /* Deep blue background */
            color: #8E9CB0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1); /* Added shadow */
            border-radius: 15px; /* Rounded corners for the navbar */
            margin-bottom: 20px; /* Space below navbar to emphasize shadow */
        }}
        .navbar a, .dropdown-content a {{
            padding: 12px;
            color: #8E9CB0;
            text-decoration: none;
            font-size: 14px;
            text-align: center;
            border-radius: 10px; /* Rounded corners for links */
        }}
        .navbar a:hover, .dropdown-content a:hover {{
            background-color: #DEE6F2; /* Slightly darker blue on hover */
        }}
        .search-container {{
            display: inline-block;
            color: #8E9CB0;
        }}
        input[type="text"] {{
            color: #8E9CB0;
            padding: 7px;
            font-size: 14px;
            border: none;
            width: 300px;
            border-radius: 10px; /* Rounded corners for the input field */
        }}
        .search-container button {{
            padding: 7px 10px;
            background: #EEF2F8;
            color: #8E9CB0;
            font-size: 14px;
            border: none;
            cursor: pointer;
            border-radius: 10px; /* Rounded corners for the button */
        }}
        .search-container button:hover {{
            background: #DEE6F2;
        }}
        .dropdown {{
            position: relative;
            display: inline-block;
        }}
        .dropbtn {{
            background-color: inherit;
            color: #8E9CB0;
            padding: 12px;
            font-size: 14px;
            border: none;
            cursor: pointer;
            border-radius: 10px; /* Rounded corners for the dropdown button */
        }}
        .dropdown-content {{
            display: none;
            position: absolute;
            background-color: #f1f1f1;
            min-width: 160px;
            box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
            z-index: 1;
            border-radius: 10px; /* Rounded corners for the dropdown content */
        }}
        .dropdown-content a {{
            color: #8E9CB0;
            padding: 12px 16px;
            text-decoration: none;
            display: block;
            text-align: left;
        }}
        .dropdown:hover .dropdown-content {{
            display: block;
            top: 100%; /* Adjust this if the dropdown still clips */
            left: 0;
        }}
    </style>

    <div class="navbar">
        <div class="search-container">
            <input type="text" placeholder="Search">
            <button type="submit">🔎︎</button>
        </div>
        <div class="dropdown">
            <button class="dropbtn">{user_name} &#9662;</button>
            <div class="dropdown-content">
                <a href="#">Profile</a>
                <a href="#">Settings</a>
                <a href="#">Logout</a>
            </div>
        </div>
    </div>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)

# Include Google Fonts for Roboto
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    </style>
    """, unsafe_allow_html=True)

# Replace 'User Name' with a dynamic user name if you have that functionality
load_navbar("User Name")

st.markdown("")
st.markdown("")
st.markdown("")

# Streamlit app
col1, colA, col2, colB, col3 = st.columns([10,1,9,1,9])
with col1:  
    
    uploaded_files = st.file_uploader("Upload PDF statements", accept_multiple_files=True, type='pdf')
    
    if uploaded_files:
        if 'data' not in st.session_state or st.button('Process Statements'):
            st.session_state.data = process_files(uploaded_files)
    
    # Display and edit data using session state
    if 'data' in st.session_state and not st.session_state.data.empty:
        edited_data = st.data_editor(st.session_state.data, num_rows="dynamic")

        if st.button('Generate Graphs'):
            st.markdown("")
            with col2:
                df_summary = edited_data[['Comercio', 'Monto']].groupby('Comercio').sum()
                df_sorted = df_summary.sort_values('Monto', ascending=False).reset_index()
                # Assuming 'Comercio' and 'Monto' columns exist
                st.bar_chart(df_sorted, x = "Comercio", y = "Monto", use_container_width=True)
            # Assuming 'Monto Acumulado' and 'Fecha' columns exist for line chart

            with col3:
                st.line_chart(edited_data[['Fecha', 'Monto Acumulado']], x = "Fecha", y = "Monto Acumulado", use_container_width=True)
    else:
        st.error('No data to display or process.')
