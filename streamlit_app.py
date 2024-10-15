import streamlit as st
import pdfplumber
import pandas as pd
import os
from datetime import datetime
import io
import openai
from streamlit.components.v1 import html
import json

st.set_page_config(layout="wide")

def load_css():
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        .card {
            background-color: #f6f8fb;  /* Light grey background */
            border: 2px solid #e1e4e8;  /* Grey border */
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            padding: 20px;
            margin-top: 10px;
            height: 400px; /* Fixed height for the card */
        }
        canvas {
            width: 100% !important;
            height: 100% !important; /* Canvas takes full height of its container */
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_css()

pd.options.display.float_format = "{:,.2f}".format

def extract_data_from_pdf(byte_data, bank_name):
    extracted_text = ""
    with pdfplumber.open(io.BytesIO(byte_data)) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"
    return extracted_text

def process_files(uploaded_files):
    final_dataframe = pd.DataFrame()
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            byte_data = uploaded_file.getvalue()
            extracted_text = extract_data_from_pdf(byte_data, 'GenericBank')
            # Parsing logic here...
            # Dummy parsed data:
            final_dataframe = pd.DataFrame({
                'Fecha': pd.date_range(start='1/1/2024', periods=10),
                'Concepto': ['Test'] * 10,
                'Monto': range(10)
            })

    final_dataframe['Monto Acumulado'] = final_dataframe['Monto'].cumsum()
    return final_dataframe

if 'data' not in st.session_state or st.sidebar.button('Process Statements'):
    uploaded_files = st.sidebar.file_uploader("Upload PDF statements", accept_multiple_files=True, type='pdf')
    if uploaded_files:
        st.session_state.data = process_files(uploaded_files)

if 'data' in st.session_state and not st.session_state.data.empty:
    edited_data = st.session_state.data
    dates_js = edited_data['Fecha'].dt.strftime('%Y-%m-%d').tolist()
    values_js = edited_data['Monto Acumulado'].tolist()

    col1, col2 = st.columns(2)
    with col1:
        chart_code = f"""
        <div class="card">
            <canvas id="myChart1"></canvas>
        </div>
        <script>
            var ctx = document.getElementById('myChart1').getContext('2d');
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
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false
                }}
            }});
        </script>
        """
        html(chart_code, height=500)

    with col2:
        df_summary = edited_data[['Concepto', 'Monto']].groupby('Concepto').sum()
        df_sorted = df_summary.sort_values('Monto', ascending=True).reset_index()
        class_js = json.dumps(df_sorted["Concepto"].tolist())
        values_js = json.dumps(df_sorted["Monto"].tolist())

        chart_code = f"""
        <div class="card">
            <canvas id="myChart2"></canvas>
        </div>
        <script>
            var ctx = document.getElementById('myChart2').getContext('2d');
            var myChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {class_js},
                    datasets: [{{
                        label: '# of Votes',
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
        """
        html(chart_code, height=500)
else:
    st.error('No data to display or process.')
