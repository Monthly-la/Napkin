import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

def extract_data_from_pdf(pdf_file, bank_name):
    """
    Extracts all text from a PDF file using pdfplumber.

    Args:
    pdf_path (str): Path to the PDF file.

    Returns:
    str: Extracted text from the PDF.
    """
    extracted_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"  # Extract and add new line
    return extracted_text
    
    edo_de_cuenta = extract_text_from_pdf(pdf_path)
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
    toc = time.clock()
    print("Tiempo de Procesamiento: " + str(round(toc - tic,2)) + "s")
    
    # Concatenate the DataFrame into the final DataFrame
    final_dataframe = pd.concat([final_dataframe, estado_de_cuenta_movimientos_df], ignore_index=True)

    final_dataframe = final_dataframe.sort_values(by = ["Fecha","Concepto"])
    final_dataframe["Monto Acumulado"] = final_dataframe["Monto"].cumsum()
    final_dataframe = final_dataframe[["Fecha", "Concepto", "Comercio", "Monto", "Monto Acumulado"]]
    return final_dataframe





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
    for label, df_group in df.groupby('Concepto'):
        plt.plot(df_group['Fecha'], df_group['Monto Acumulado'], label=label)
    plt.title('Credit Card Movements Over Time')
    plt.xlabel('Fecha')
    plt.ylabel('Monto Acumulado')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return plt

def plot_bar_graph(df):
    plt.figure(figsize=(10, 5))
    total_per_concept = df.groupby('Concepto')['Monto Acumulado'].sum().sort_values()
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
