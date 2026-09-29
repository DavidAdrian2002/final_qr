import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. Definimos el formato exacto de salida que requerimos (Esquema Pydantic)
class AlumnoExtraido(BaseModel):
    nombre: str = Field(description="Nombre o nombres del alumno")
    apellido: str = Field(description="Apellido o apellidos del alumno")
    sexo: str = Field(description="Sexo del alumno: 'M' para Masculino, 'F' para Femenino")

class ListaAlumnosExtraida(BaseModel):
    alumnos: list[AlumnoExtraido]

# Configura tu API Key aquí o pásala como variable de entorno
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def procesar_documento_alumnos(ruta_archivo: str) -> list[dict]:
    """
    Sube un archivo (PDF, JPG, PNG) a la API de Gemini y retorna
    una lista de diccionarios con la información estructurada de los alumnos.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Subir el archivo temporalmente a la API de Google
    file_ref = client.files.upload(file=ruta_archivo)

    prompt = """
    Analiza detalladamente este documento o imagen y extrae la lista completa de alumnos.
    Para cada alumno identifica con precisión:
    - nombre (solo los nombres)
    - apellido (solo los apellidos)
    - sexo ('M' o 'F'. Si no está explícito en la lista, infiérelo según el nombre del alumno).

    Instrucciones estrictas:
    1. Omite encabezados, nombres de escuelas, nombres de profesores, materias o fechas.
    2. Mantén el orden original de la lista.
    3. Si la imagen o PDF contiene texto manuscrito, haz tu mejor esfuerzo de lectura.
    """

    try:
        # Generar contenido usando el modelo rápido con respuesta JSON estructurada
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[file_ref, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ListaAlumnosExtraida,
                temperature=0.1,  # Baja temperatura para mayor precisión y menos 'creatividad'
            ),
        )

        # Eliminar el archivo de los servidores de Google tras procesarlo
        client.files.delete(name=file_ref.name)

        # Convertir la respuesta de texto JSON a objeto/lista de Python
        resultado = json.loads(response.text)
        return resultado.get("alumnos", [])

    except Exception as e:
        print(f"Error procesando con Gemini: {e}")
        raise e