import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import io
import openai
from streamlit.components.v1 import html
import json

st.set_page_config(layout="wide")

# Function to load custom CSS
def load_css():
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        .badge {
            background-color: #EEF2F8;
            color: gray;
            padding: 8px;
            border-radius: 5px;
            font-family: 'Roboto', sans-serif;
            font-weight: 100;
            font-size: x-small;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            display: flex;         /* Using flexbox */
            justify-content: center; /* Center horizontally */
            align-items: center;     /* Center vertically */
            text-align: center;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Load the custom CSS
load_css()

hide_streamlit_style = """
<style>

footer {visibility: hidden;}
footer:after {
	content:'goodbye'; 
	visibility: visible;
	display: block;
	position: relative;
	#background-color: red;
	padding: 5px;
	top: 2px;
}
.css-hi6a2p {padding-top: 0rem;}
.stDeployButton {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

pd.options.display.float_format = "{:,.2f}".format
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



def load_navbar(user_name, image_url):

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
            font-size: 12px;
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
            font-size: 12px;
            border: none;
            width: 300px;
            border-radius: 10px; /* Rounded corners for the input field */
        }}
        .search-container button {{
            padding: 7px 10px;
            background: #EEF2F8;
            color: #8E9CB0;
            font-size: 12px;
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
            font-size: 12px;
            border: none;
            cursor: pointer;
            border-radius: 10px; /* Rounded corners for the dropdown button */
        }}

        .profile-img {{
            width: 32px; /* Set the image size */
            height: 32px;
            border-radius: 50%; /* Circular image */
            margin-right: 8px; /* Space between image and text */
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
            <input type="text" placeholder="Search...">
            <button type="submit">🔎︎</button>
        </div>
        <div class="dropdown">
            <button class="dropbtn">
                <img src="{image_url}" alt="Profile Image" class="profile-img">
                {user_name} &#9662;
            </button>
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

load_navbar("Sergio Sepúlveda", "https://media.licdn.com/dms/image/v2/D5603AQHuQMpgsshaQA/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1725653082255?e=1734566400&v=beta&t=ElSClXmLUMGHlxymSVNBc1lctfPPIM1H2Hc5ltzmcAc")

st.markdown("")
st.markdown("")
st.markdown("")

# Streamlit app
tab1, tab2, tab3 = st.tabs(["SELECT CARDS 💳", "UPLOAD INFO 📤", "DASHBOARD 📊"])
graphs = False
with tab1:
	st.markdown("")
	st.markdown("")
	st.markdown("")
	bank_cards = {
	    'ABC Capital': ['Ualá ABC (ABC Capital)'],
	    'Afirme': ['HEB Afirme', 'Afirme Clásica', 'Tigres Afirme', 'Afirme Platinum'],
	    'BBVA': [
	        'Crea BBVA', 'Azul BBVA', 'IPN BBVA', 'Rayados BBVA', 'Vive BBVA', 
	        'Afinidad UNAM BBVA', 'Oro BBVA', 'Platinum BBVA', 'Infinite BBVA'
	    ],
	    'BanBajío': [
	        'Visa Clásica Garantizada Internacional (Bajío)', 'Visa Clásica Internacional (Bajío)', 
	        'Visa Oro Internacional (Bajío)', 'Visa Platinum Internacional (Bajío)'
	    ],
	    'BanCoppel': ['Tarjeta de Crédito BanCoppel', 'BanCoppel Oro'],
	    'Banco Azteca': ['Oro (Banco Azteca)'],
	    'Banorte': [
	        'Banorte Básica', 'Banorte Conmigo', 'AT&T (Banorte)', 'Clásica (Banorte)', 
	        'Tarjeta 40 (Banorte)', 'Ke Buena (Banorte)', 'W Radio (Banorte)', 'Mujer Banorte', 
	        'Oro (Banorte)', 'Selección Nacional (Banorte)', 'Banorte Por Ti', 'Marriott Bonvoy (Banorte)', 
	        'AT&T Elite (Banorte)', 'Platinum (Banorte)', 'United (Banorte)', 'Marriott Bonvoy Inspire (Banorte)', 
	        'United Universe (Banorte)', 'Infinite (Banorte)'
	    ],
	    'Banregio': [
	        'Clásica (Banregio)', 'Gold (Banregio)', 'Hey (Banregio)', 'Más (Banregio)', 
	        'Platinum (Banregio)', 'Tarjeta Banregio'
	    ],
	    'Citibanamex': [
	        'Citibanamex Simplicity', 'Costco Citibanamex', 'Teletón Citibanamex', 'The Home Depot Citibanamex', 
	        'Affinity Card Citibanamex', 'Clásica Citibanamex', 'Citibanamex Rewards', 'Oro Citibanamex', 
	        'Citibanamex Premier', 'Platinum Citibanamex', 'Citibanamex Prestige'
	    ],
	    'HSBC': [
	        'HSBC 2Now', 'HSBC Zero', 'HSBC Viva', 'HSBC Air', 'HSBC Advance Platinum', 
	        'HSBC Viva Plus', 'HSBC Premier World Elite'
	    ],
	    'INVEX': [
	        'Volaris INVEX 0', 'Despegar INVEX Gold', 'Volaris INVEX', 
	        'Despegar INVEX Platinum', 'Volaris INVEX 2.0'
	    ],
	    'Inbursa': [
	        'Inbursa Clásica', 'Inbursa Oro', 'Inbursa Óptima', "Inbursa Sam's Club", 
	        'Inbursa Walmart', 'Inbursa Black American Express'
	    ],
	    'Mifel': ['Mifel Oro', 'Mifel Platino', 'Mifel World Elite'],
	    'Santander': [
	        'LikeU (Santander)', 'Samsung Members (Santander)', 'Santander Aeroméxico Blanca', 
	        'Santander American Express', 'Santander Free', 'Santander Zero', 'Fiesta Rewards Oro (Santander)', 
	        'Fiesta Rewards Platino (Santander)', 'Santader Platinum', 'Santander Aeroméxico Platinum', 
	        'Santander Aeroméxico Infinite', 'Santander World Elite'
	    ],
	    'Scotiabank': [
	        'IDEAL Scotiabank', 'Scotia Travel Clásica', 'Scotia Travel Oro', 'Scotia Travel Platinum', 
	        'Scotiabank AAdvantage Platinum', 'Scotia Travel World Elite', 'Scotiabank AAdvantage World Elite', 
	        'Scotiabank Visa Signature'
	    ]
	}

	# Define the layout: 3 columns
	pad1, col1, pad2, col2, pad3, col3, pad4, col4, pad5 = st.columns([1,4,1,4,1,4,1,4,1])
	
	# Column 1: Number of cards input
	with col1:
		num_cards = st.number_input("Enter the number of credit cards:", min_value=1, max_value=10, step=1, value=1, key='num_cards')
	
	# Column 2: Dropdowns for selecting the bank
	with col2:
		banks_selected = []
		for i in range(int(num_cards)):
		    banks_selected.append(st.selectbox(f"Select the bank for card {i + 1}:",
						       options=list(bank_cards.keys()),
						       key=f"bank_{i}"))
	
	# Column 3: Dropdowns for selecting the card type based on selected bank
	with col3:
		cards_selected = []
		for i in range(int(num_cards)):
		    cards_selected.append(st.selectbox(f"Select the type for card {i + 1}:",
						       options=bank_cards[banks_selected[i]],
						       key=f"card_type_{i}"))
	     		st.markdown("")
	     		
		
	# Submit button
	if st.button("Submit"):
		st.write("Submitted Information:")
		for i in range(int(num_cards)):
		    st.write(f"Card {i + 1}: Bank - {banks_selected[i]}, Card Type - {cards_selected[i]}")
		
with tab2: 
	st.markdown("")
	st.markdown("")
	padA, col1, colA, col2, padB= st.columns([1,11,2,11,2])
	with col1:
		uploaded_files = st.file_uploader("Upload PDF statements", accept_multiple_files=True, type='pdf')
	
		if uploaded_files:
		    if 'data' not in st.session_state or st.button('Process Statements'):
	     		st.session_state.data = process_files(uploaded_files)
	
	with col2:
		st.markdown("")
		st.markdown("")
		# Display and edit data using session state
		if 'data' in st.session_state and not st.session_state.data.empty:
  			edited_data = st.data_editor(st.session_state.data, num_rows="dynamic", hide_index=True)
		if st.button('Generate Graphs'):
			graphs = True

        
with tab3:
    st.markdown("")
    if graphs:
        col2, colB, col3 = st.columns([10,1,10])
        st.markdown("")
        with col2:
            st.markdown("<span class = 'badge'>MOVIMIENTOS DE SALDO (MXN)</span>", unsafe_allow_html=True)
            if 'data' in st.session_state and not st.session_state.data.empty:
                dates_js = edited_data['Fecha'].dt.strftime('%Y-%m-%d').tolist()  # Format dates as strings
                values_js = edited_data['Monto Acumulado'].tolist()
                
                # Chart with actual data
                chart_code = f"""
                    <!DOCTYPE html>
                    <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                            <title>Area Chart with Actual Data</title>
                            <style>
                                canvas {{
                                    width: 100% !important;
                                    height: auto !important;
                                }}
                            </style>
                        </head>
                        <body>
                            <div style="width: 100%;">
                                <canvas id="myChart"></canvas>
                            </div>
                            <script>
                                var ctx = document.getElementById('myChart').getContext('2d');
                                var myChart = new Chart(ctx, {{
                                    type: 'line',
                                    data: {{
                                        labels: {dates_js},
                                        datasets: [{{
                                            label: 'Monto Acumulado',
                                            data: {values_js},
                                            fill: true,
                                            backgroundColor: 'rgba(78, 115, 223, 0.1)',
                                            borderColor: 'rgb(78, 115, 223)',
                                            tension: 0.3
                                        }}]
                                    }}
                                }});
                            </script>
                        </body>
                    </html>
                    """
                html(chart_code, height=500)
    
        with col3:
            st.markdown("<span class = 'badge'>EGRESO TOTAL POR COMERCIO (MXN)</span>", unsafe_allow_html=True)
            if 'data' in st.session_state and not st.session_state.data.empty:
                df_summary = edited_data[['Comercio', 'Monto']].groupby('Comercio').sum()
                df_sorted = df_summary.sort_values('Monto', ascending=True).reset_index()
                class_js = json.dumps(df_sorted["Comercio"].tolist())  # Convert Python list to JSON for JavaScript
                values_js = json.dumps(df_sorted["Monto"].tolist())  # Convert Python list to JSON for JavaScript
            
                # Correctly formatted JavaScript and HTML for bar chart
                chart_code = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                    <title>Responsive Bar Chart</title>
                    <style>
                        canvas {{
                            width: 100% !important;
                            height: auto !important;
                        }}
                    </style>
                </head>
                <body>
                    <div style="width: 100%;">
                        <canvas id="myChart"></canvas>
                    </div>
                    <script>
                        var ctx = document.getElementById('myChart').getContext('2d');
                        var myChart = new Chart(ctx, {{
                            type: 'bar',
                            data: {{
                                labels: {class_js},
                                datasets: [{{
                                    label: 'Monto Total (MXN)',
                                    data: {values_js},
                                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                    borderColor: 'rgba(255, 99, 132, 1)',
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {{
                                    y: {{
                                        beginAtZero: true
                                    }}
                                }}
                            }}
                        }});
                    </script>
                </body>
                </html>
                """
                html(chart_code, height=500)
            else:
                st.error('No data to display or process.')
    else:
        st.error('No data to display or process.')
