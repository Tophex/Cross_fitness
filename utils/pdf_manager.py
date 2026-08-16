import os
from datetime import datetime
from fpdf import FPDF

def generar_recibo_pdf(nombre_cliente: str, cedula: str, nombre_plan: str, precio: float, fecha_inicio: str, fecha_vencimiento: str) -> str:
    """
    Genera un recibo de pago en PDF y lo abre automáticamente.
    """
    # Asegurar que existe la carpeta
    os.makedirs("recibos", exist_ok=True)
    
    # Nombre de archivo dinámico
    fecha_emision = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"recibo_{cedula}_{fecha_emision}.pdf"
    ruta_pdf = os.path.join("recibos", nombre_archivo)
    
    # Crear PDF (formato Ticket / Recibo)
    pdf = FPDF(format='A5')
    pdf.add_page()
    
    # Título centrado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RECIBO DE PAGO - GIMNASIO", ln=True, align='C')
    pdf.ln(5)
    
    # Datos generales
    pdf.set_font("Arial", '', 12)
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 10, f"Fecha de emisión: {fecha_hoy}", ln=True)
    pdf.ln(5)
    
    # Datos del cliente
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Datos del Cliente:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Nombre: {nombre_cliente}", ln=True)
    pdf.cell(0, 8, f"Cédula: {cedula}", ln=True)
    pdf.ln(5)
    
    # Detalle del servicio
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Detalle del Servicio:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Plan adquirido: {nombre_plan}", ln=True)
    pdf.cell(0, 8, f"Valor pagado: ${precio:,.2f}", ln=True)
    pdf.ln(5)
    
    # Vigencia
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Vigencia de la Membresía:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Desde: {fecha_inicio}", ln=True)
    pdf.cell(0, 8, f"Hasta: {fecha_vencimiento}", ln=True)
    
    # Guardar archivo
    pdf.output(ruta_pdf)
    
    # Abrir archivo (multiplataforma básico)
    try:
        if os.name == 'nt':
            os.startfile(ruta_pdf)
        else:
            import subprocess
            subprocess.run(["open", ruta_pdf])
    except Exception as e:
        print(f"No se pudo abrir el PDF automáticamente: {e}")
        
    return ruta_pdf
