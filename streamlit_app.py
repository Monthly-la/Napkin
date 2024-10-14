import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

def extract_data_from_pdf(pdf_file, bank_name):
    """
    Placeholder function to extract data from PDF.
    This function needs to be tailored based on specific bank statement formats.
    """
    transactions = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                if line.strip() and '$' in line:
                    parts = line.split()
                    date_str, amount = parts[0], parts[-1].replace(',', '').replace('$', '')
                    date = datetime.strptime(date_str, '%m/%d/%Y')
                    concept = " ".join(parts[1:-1])
                    transactions.append([date, concept, float(amount)])
                    
    return pd.DataFrame(transactions, columns=['Date', 'Concept', 'Amount'])

def process_files(uploaded_files):
    all_data = pd.DataFrame()
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            # Assuming bank name can be inferred from file name or another method
            bank_name = 'GenericBank'
            bytes_data = uploaded_file.read()
            df = extract_data_from_pdf(bytes_data, bank_name)
            all_data = pd.concat([all_data, df], ignore_index=True)
    return all_data

def plot_line_graph(df):
    plt.figure(figsize=(10, 5))
    for label, df_group in df.groupby('Concept'):
        plt.plot(df_group['Date'], df_group['Amount'], label=label)
    plt.title('Credit Card Movements Over Time')
    plt.xlabel('Date')
    plt.ylabel('Amount')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return plt

def plot_bar_graph(df):
    plt.figure(figsize=(10, 5))
    total_per_concept = df.groupby('Concept')['Amount'].sum().sort_values()
    total_per_concept.plot(kind='barh')
    plt.title('Total Spent Per Commercial Provider')
    plt.xlabel('Total Amount')
    plt.ylabel('Provider')
    plt.tight_layout()
    return plt

# Streamlit app
st.title('Credit Card Statement Processor')

uploaded_files = st.file_uploader("Upload PDF statements", accept_multiple_files=True, type='pdf')
if uploaded_files:
    processed_data = process_files(uploaded_files)
    if st.button('Process Statements'):
        if not processed_data.empty:
            st.write('Processed Data', processed_data)
            line_graph = plot_line_graph(processed_data)
            bar_graph = plot_bar_graph(processed_data)
            
            st.pyplot(line_graph)
            st.pyplot(bar_graph)
        else:
            st.error('No data to display.')
