import uuid
import os
import os
import secrets  # Para generar los qr_tokens únicos de cada alumno


from utils.qr import generar_qr
from flask import send_file
from datetime import datetime
from zoneinfo import ZoneInfo
from docx import Document
from docx.shared import Inches
from flask import *
from utils.db import *
from flask import request, render_template, redirect, url_for, session, flash
from servicios_ia import procesar_documento_alumnos

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Image
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    flash,
    send_file
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from utils.db import init_db, get_connection

app = Flask(__name__)

init_db()

app.secret_key = "super_secret_key"

UPLOAD_FOLDER = "static/img/alumnos"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


asistencias_temp = {}

# =========================
# INICIO
# =========================
@app.route("/")
def home():

    if "docente_id" in session:
        return redirect("/dashboard")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM docentes")
    total = cursor.fetchone()["total"]

    conn.close()

    if total == 0:
        return redirect("/register")

    return redirect("/login")


# =========================
# REGISTRO
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        usuario = request.form["usuario"]
        password = request.form["password"]

        # Verificar si usuario existe
        cursor.execute("""
        SELECT *
        FROM docentes
        WHERE usuario = %s
        """, (usuario,))

        existe = cursor.fetchone()

        if existe:

            flash("El usuario ya existe")

            conn.close()

            return redirect("/register")

        # Hash seguro
        password_hash = generate_password_hash(password)

        # Crear docente
        cursor.execute("""
        INSERT INTO docentes (
            nombre,
            apellido,
            usuario,
            password
        )
        VALUES (%s, %s, %s, %s)
        """, (
            nombre,
            apellido,
            usuario,
            password_hash
        ))

        conn.commit()

        conn.close()

        flash("Cuenta creada correctamente")

        return redirect("/login")

    conn.close()

    return render_template("register.html")


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM docentes
        WHERE usuario = %s
        """, (usuario,))

        docente = cursor.fetchone()

        conn.close()

        if docente:

            if check_password_hash(
                docente["password"],
                password
            ):

                session["docente_id"] = docente["id"]
                session["docente_nombre"] = docente["nombre"]

                return redirect("/dashboard")

        error = "Usuario o contraseña incorrectos"

    return render_template(
        "login.html",
        error=error
    )



# =========================
# ESCUELAS
# =========================
@app.route("/escuelas")
def escuelas():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT escuelas.*
    FROM escuelas

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    escuelas = cursor.fetchall()

    conn.close()

    return render_template(
        "escuelas.html",
        escuelas=escuelas
    )


# =========================
# CREAR ESCUELA
# =========================
@app.route("/escuelas/nueva", methods=["GET", "POST"])
def nueva_escuela():

    if "docente_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        nombre = request.form["nombre"]
        numero = request.form["numero"]
        localidad = request.form["localidad"]

        conn = get_connection()
        cursor = conn.cursor()

        # Crear escuela
        cursor.execute("""
        INSERT INTO escuelas (
            nombre,
            numero,
            localidad
        )
        VALUES (%s, %s, %s)
        RETURNING id
        """, (
            nombre,
            numero,
            localidad
        ))

        escuela_id = cursor.fetchone()["id"]

        # Asociar docente
        cursor.execute("""
        INSERT INTO docente_escuelas (
            docente_id,
            escuela_id
        )
        VALUES (%s, %s)
        """, (
            session["docente_id"],
            escuela_id
        ))

        conn.commit()
        conn.close()

        return redirect("/escuelas")

    return render_template("nueva_escuela.html")


# =========================
# ELIMINAR ESCUELA
# =========================
@app.route("/escuelas/eliminar/<int:id>")
def eliminar_escuela(id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Eliminar relación
    cursor.execute("""
    DELETE FROM docente_escuelas
    WHERE docente_id = %s
    AND escuela_id = %s
    """, (
        session["docente_id"],
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/escuelas")

    # =========================
    # RELACION DOCENTE-ESCUELA
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docente_escuelas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        docente_id INTEGER NOT NULL,
        escuela_id INTEGER NOT NULL,

        FOREIGN KEY(docente_id)
        REFERENCES docentes(id),

        FOREIGN KEY(escuela_id)
        REFERENCES escuelas(id)
    )
    """)

    conn.commit()
    conn.close()

# =========================
# LISTAR GRADOS
# =========================
@app.route("/grados")
def grados():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        grados.id,
        grados.nombre,
        escuelas.nombre as escuela_nombre

    FROM grados

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    grados = cursor.fetchall()

    conn.close()

    return render_template(
        "grados.html",
        grados=grados
    )


# =========================
# NUEVO GRADO
# =========================
@app.route("/grados/nuevo", methods=["GET", "POST"])
def nuevo_grado():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener escuelas del docente
    cursor.execute("""
    SELECT escuelas.*
    FROM escuelas

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    escuelas = cursor.fetchall()

    if request.method == "POST":

        nombre = request.form["nombre"]
        escuela_id = request.form["escuela_id"]

        cursor.execute("""
        INSERT INTO grados (
            nombre,
            escuela_id
        )
        VALUES (%s, %s)
        """, (
            nombre,
            escuela_id
        ))

        conn.commit()
        conn.close()

        return redirect("/grados")

    conn.close()

    return render_template(
        "nuevo_grado.html",
        escuelas=escuelas
    )


# =========================
# ELIMINAR GRADO
# =========================
@app.route("/grados/eliminar/<int:id>")
def eliminar_grado(id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM grados
    WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/grados")

# =========================
# ALUMNOS
# =========================
@app.route("/alumnos")
def vista_alumnos():
    if "docente_id" not in session:
        return redirect("/login")

    docente_id = session["docente_id"]
    escuela_id = request.args.get("escuela_id")
    grado_id = request.args.get("grado_id")

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Obtener las escuelas del docente uniendo con docente_escuelas
    cursor.execute("""
        SELECT e.* 
        FROM escuelas e
        JOIN docente_escuelas de ON e.id = de.escuela_id
        WHERE de.docente_id = %s
    """, (docente_id,))
    escuelas = cursor.fetchall()

    # 2. Obtener los grados del docente
    if escuela_id:
        cursor.execute("SELECT * FROM grados WHERE escuela_id = %s", (escuela_id,))
    else:
        cursor.execute("""
            SELECT g.* 
            FROM grados g
            JOIN escuelas e ON g.escuela_id = e.id
            JOIN docente_escuelas de ON e.id = de.escuela_id
            WHERE de.docente_id = %s
        """, (docente_id,))
    
    grados = cursor.fetchall()

    # 3. Obtener los alumnos del grado seleccionado
    alumnos = []
    if grado_id:
        cursor.execute("""
            SELECT * FROM alumnos 
            WHERE grado_id = %s 
            ORDER BY apellido, nombre
        """, (grado_id,))
        alumnos = cursor.fetchall()

    conn.close()

    return render_template(
        "alumnos.html",
        escuelas=escuelas,
        grados=grados,
        alumnos=alumnos,
        escuela_id_seleccionada=escuela_id,
        grado_id_seleccionado=grado_id
    )

# =========================
# NUEVO ALUMNO
# =========================
@app.route("/alumnos/nuevo", methods=["GET", "POST"])
def nuevo_alumno():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        grados.id,
        grados.nombre,
        escuelas.nombre as escuela_nombre

    FROM grados

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    grados = cursor.fetchall()

    if request.method == "POST":

        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        dni = request.form["dni"]
        sexo = request.form["sexo"]
        grado_id = request.form["grado_id"]

        qr_token = str(uuid.uuid4())

        foto = None

        # =========================
        # FOTO
        # =========================
        archivo = request.files.get("foto")

        if archivo and archivo.filename != "":

            extension = archivo.filename.split(".")[-1]

            nombre_foto = f"{uuid.uuid4()}.{extension}"

            ruta = os.path.join(
                app.config["UPLOAD_FOLDER"],
                nombre_foto
            )

            archivo.save(ruta)

            foto = nombre_foto

        cursor.execute("""
        INSERT INTO alumnos (
            nombre,
            apellido,
            dni,
            sexo,
            foto,
            qr_token,
            grado_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            nombre,
            apellido,
            dni,
            sexo,
            foto,
            qr_token,
            grado_id
        ))

        conn.commit()
        conn.close()

        flash("Alumno creado correctamente")

        return redirect("/alumnos")

    conn.close()

    return render_template(
        "nuevo_alumno.html",
        grados=grados
    )


# =========================
# DESACTIVAR ALUMNO
# =========================
@app.route("/alumnos/desactivar/<int:id>")
def desactivar_alumno(id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE alumnos
    SET activo = 0
    WHERE id = %s
    """, (id,))

    conn.commit()
    conn.close()

    flash("Alumno desactivado")

    return redirect("/alumnos")

# =========================
# VER QR
# =========================
@app.route("/alumnos/qr/<int:id>")
def ver_qr(id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE id = %s
    """, (id,))

    alumno = cursor.fetchone()

    conn.close()

    if not alumno:
        return "Alumno no encontrado"

    generar_qr(alumno["qr_token"])

    return render_template(
        "ver_qr.html",
        alumno=alumno
    )


# =========================
# DESCARGAR QR
# =========================
@app.route("/alumnos/qr/descargar/<int:id>")
def descargar_qr(id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE id = %s
    """, (id,))

    alumno = cursor.fetchone()

    conn.close()

    if not alumno:
        return "Alumno no encontrado"

    ruta = generar_qr(alumno["qr_token"])

    return send_file(
        ruta,
        as_attachment=True
    )

# =========================
# TOMAR ASISTENCIA
# =========================
@app.route("/asistencia")
def asistencia():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        grados.id,
        grados.nombre,
        escuelas.nombre as escuela_nombre

    FROM grados

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    grados = cursor.fetchall()

    conn.close()

    return render_template(
        "asistencia.html",
        grados=grados
    )


# =========================
# INICIAR ASISTENCIA
# =========================
@app.route("/asistencia/iniciar", methods=["POST"])
def iniciar_asistencia():

    if "docente_id" not in session:
        return redirect("/login")

    grado_id = str(request.form["grado_id"])

    asistencias_temp[grado_id] = []

    return redirect(f"/asistencia/escanear/{grado_id}")


# =========================
# PANTALLA ESCANEO
# =========================
@app.route("/asistencia/escanear/<int:grado_id>")
def escanear_asistencia(grado_id):

    if "docente_id" not in session:
        return redirect("/login")

    return render_template(
        "escanear.html",
        grado_id=grado_id
    )


# =========================
# REGISTRAR ESCANEO
# =========================
@app.route("/asistencia/registrar", methods=["POST"])
def registrar_asistencia():

    if "docente_id" not in session:
        return {"error": "No autorizado"}, 401

    token = request.form["token"]
    grado_id = str(request.form["grado_id"])
    grado_id_int = int(grado_id)
    estado = request.form["estado"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE qr_token = %s
    AND grado_id = %s
    """, (
        token,
        grado_id_int
    ))

    alumno = cursor.fetchone()

    if not alumno:
        conn.close()
        return {"error": "Alumno no encontrado"}

    # Evitar duplicados
    for item in asistencias_temp.get(grado_id, []):

        if item["alumno_id"] == alumno["id"]:
            conn.close()
            return {"error": "Alumno ya registrado"}

    # HORA CORREGIDA PARA ARGENTINA:
    hora = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).strftime("%H:%M:%S")

    data = {
        "alumno_id": alumno["id"],
        "nombre": alumno["nombre"],
        "apellido": alumno["apellido"],
        "sexo": alumno["sexo"],
        "estado": estado,
        "hora": hora
    }

    asistencias_temp[grado_id].append(data)

    conn.close()

    return data


# =========================
# CERRAR ASISTENCIA
# =========================
@app.route("/asistencia/cerrar/<int:grado_id>")
def cerrar_asistencia(grado_id):

    if "docente_id" not in session:
        return redirect("/login")

    # Normalizar tipos
    grado_id_int = int(grado_id)
    grado_id_str = str(grado_id)

    conn = get_connection()
    cursor = conn.cursor()

    fecha = datetime.now().strftime("%Y-%m-%d")

    # Obtener registros temporales
    registrados = asistencias_temp.get(grado_id_str, [])

    registrados_ids = []

    # =========================
    # GUARDAR PRESENTES/DEMORAS
    # =========================
    for item in registrados:

        registrados_ids.append(item["alumno_id"])

        cursor.execute("""
        INSERT INTO asistencias (
            alumno_id,
            fecha,
            hora,
            estado,
            grado_id
        )
        VALUES (%s, %s, %s, %s, %s)
        """, (
            item["alumno_id"],
            fecha,
            item["hora"],
            item["estado"],
            grado_id_int
        ))

    # =========================
    # OBTENER TODOS LOS ALUMNOS
    # =========================
    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE grado_id = %s
    AND activo = 1
    """, (grado_id_int,))

    alumnos = cursor.fetchall()

    # =========================
    # REGISTRAR AUSENTES
    # =========================
    for alumno in alumnos:

        if alumno["id"] not in registrados_ids:

            cursor.execute("""
            INSERT INTO asistencias (
                alumno_id,
                fecha,
                hora,
                estado,
                grado_id
            )
            VALUES (%s, %s, %s, %s, %s)
            """, (
                alumno["id"],
                fecha,
                "--:--",
                "Ausente",
                grado_id_int
            ))

    conn.commit()
    conn.close()

    # Limpiar memoria temporal
    asistencias_temp.pop(grado_id_str, None)

    flash("Asistencia guardada correctamente")

    return redirect("/dashboard")

# =========================
# HISTORIAL
# =========================
@app.route("/historial", methods=["GET"])
def historial():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener grados
    cursor.execute("""
    SELECT
        grados.id,
        grados.nombre,
        escuelas.nombre as escuela_nombre

    FROM grados

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    grados = cursor.fetchall()

    grado_id = request.args.get("grado_id")
    fecha = request.args.get("fecha")

    asistencias = []

    if grado_id and fecha:

        cursor.execute("""
        SELECT
            asistencias.*,

            alumnos.nombre,
            alumnos.apellido,
            alumnos.sexo,

            grados.nombre as grado_nombre

        FROM asistencias

        INNER JOIN alumnos
        ON asistencias.alumno_id = alumnos.id

        INNER JOIN grados
        ON asistencias.grado_id = grados.id

        WHERE asistencias.grado_id = %s
        AND asistencias.fecha = %s

        ORDER BY alumnos.apellido ASC
        """, (
            grado_id,
            fecha
        ))

        asistencias = cursor.fetchall()

    conn.close()

    return render_template(
        "historial.html",
        grados=grados,
        asistencias=asistencias
    )
# =========================
# GENERAR QR MASIVO
# =========================
@app.route("/qr")
def qr_grados():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        grados.id,
        grados.nombre,
        escuelas.nombre as escuela_nombre

    FROM grados

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    grados = cursor.fetchall()

    conn.close()

    return render_template(
        "qr_grados.html",
        grados=grados
    )
# =========================
# VER QR POR GRADO
# =========================
@app.route("/qr/grado/<int:grado_id>")
def qr_por_grado(grado_id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        alumnos.*,
        grados.nombre as grado_nombre

    FROM alumnos

    INNER JOIN grados
    ON alumnos.grado_id = grados.id

    WHERE alumnos.grado_id = %s
    AND alumnos.activo = 1

    ORDER BY alumnos.apellido ASC
    """, (grado_id,))

    alumnos = cursor.fetchall()

    conn.close()

    # Generar QR si no existen
    for alumno in alumnos:
        generar_qr(alumno["qr_token"])

    return render_template(
        "qr_grado.html",
        alumnos=alumnos
    )
# =========================
# PDF QR MASIVO
# =========================
@app.route("/qr/pdf/<int:grado_id>")
def qr_pdf(grado_id):

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE grado_id = %s
    AND activo = 1

    ORDER BY apellido ASC
    """, (grado_id,))

    alumnos = cursor.fetchall()

    conn.close()

    pdf_path = f"qr_grado_{grado_id}.pdf"

    doc = SimpleDocTemplate(pdf_path)

    elementos = []

    styles = getSampleStyleSheet()

    titulo = Paragraph(
        "QR de Alumnos",
        styles["Title"]
    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 20))

    datos = []

    fila = []

    contador = 0

    for alumno in alumnos:

        ruta_qr = generar_qr(alumno["qr_token"])

        qr_img = Image(
            ruta_qr,
            width=120,
            height=120
        )

        texto = Paragraph(
            f"""
            {alumno['apellido']},
            {alumno['nombre']}
            """,
            styles["BodyText"]
        )

        contenido = [qr_img, texto]

        fila.append(contenido)

        contador += 1

        if contador % 3 == 0:

            datos.append(fila)

            fila = []

    if fila:
        datos.append(fila)

    tabla = Table(datos)

    tabla.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 20)
    ]))

    elementos.append(tabla)

    doc.build(elementos)

    return send_file(
        pdf_path,
        as_attachment=True
    )
# =========================
# EXPORTAR PDF
# =========================
@app.route("/historial/pdf")
def historial_pdf():

    if "docente_id" not in session:
        return redirect("/login")

    grado_id = request.args.get("grado_id")
    fecha = request.args.get("fecha")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        asistencias.estado,
        asistencias.hora,

        alumnos.nombre,
        alumnos.apellido,

        grados.nombre as grado_nombre,
        escuelas.nombre as escuela_nombre

    FROM asistencias

    INNER JOIN alumnos
    ON asistencias.alumno_id = alumnos.id

    INNER JOIN grados
    ON asistencias.grado_id = grados.id

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    WHERE asistencias.grado_id = %s
    AND asistencias.fecha = %s

    ORDER BY alumnos.apellido ASC
    """, (
        grado_id,
        fecha
    ))

    registros = cursor.fetchall()

    conn.close()

    pdf_path = "reporte_asistencia.pdf"

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elementos = []

    titulo = Paragraph(
        f"Reporte de Asistencia - {fecha}",
        styles["Title"]
    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 20))

    datos = [[
        "Alumno",
        "Estado",
        "Hora"
    ]]

    for item in registros:

        datos.append([
            f"{item['apellido']}, {item['nombre']}",
            item["estado"],
            item["hora"]
        ])

    tabla = Table(datos)

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),

        ("GRID", (0,0), (-1,-1), 1, colors.black),

        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        ("BOTTOMPADDING", (0,0), (-1,0), 12)
    ]))

    elementos.append(tabla)

    doc.build(elementos)

    return send_file(
        pdf_path,
        as_attachment=True
    )
# =========================
# REPORTES
# =========================
@app.route("/reportes", methods=["GET", "POST"])
def reportes():

    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener grados del docente
    cursor.execute("""
    SELECT
        grados.id,
        grados.nombre,
        escuelas.nombre as escuela_nombre

    FROM grados

    INNER JOIN escuelas
    ON grados.escuela_id = escuelas.id

    INNER JOIN docente_escuelas
    ON escuelas.id = docente_escuelas.escuela_id

    WHERE docente_escuelas.docente_id = %s
    """, (session["docente_id"],))

    grados = cursor.fetchall()

    conn.close()

    return render_template(
        "reportes.html",
        grados=grados
    )
# =========================
# GENERAR REPORTE
# =========================
@app.route("/reportes/generar", methods=["POST"])
def generar_reporte():

    if "docente_id" not in session:
        return redirect("/login")

    grado_id = request.form["grado_id"]
    mes = request.form["mes"]
    dias_habiles = int(
        request.form["dias_habiles"]
    )

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener alumnos
    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE grado_id = %s
    AND activo = 1
    ORDER BY apellido ASC
    """, (grado_id,))

    alumnos = cursor.fetchall()

    reporte = []

    for alumno in alumnos:

        # Presentes
        cursor.execute("""
        SELECT COUNT(*) as total
        FROM asistencias
        WHERE alumno_id = %s
        AND estado = 'Presente'
        AND fecha LIKE %s
        """, (
            alumno["id"],
            f"{mes}%"
        ))

        presentes = cursor.fetchone()["total"]

        # Demoras
        cursor.execute("""
        SELECT COUNT(*) as total
        FROM asistencias
        WHERE alumno_id = %s
        AND estado = 'Demora'
        AND fecha LIKE %s
        """, (
            alumno["id"],
            f"{mes}%"
        ))

        demoras = cursor.fetchone()["total"]

        # Ausentes
        cursor.execute("""
        SELECT COUNT(*) as total
        FROM asistencias
        WHERE alumno_id = %s
        AND estado = 'Ausente'
        AND fecha LIKE %s
        """, (
            alumno["id"],
            f"{mes}%"
        ))

        ausentes = cursor.fetchone()["total"]

        porcentaje = round(
            (
                (presentes + demoras)
                / dias_habiles
            ) * 100,
            1
        )

        reporte.append({

            "apellido": alumno["apellido"],
            "nombre": alumno["nombre"],
            "presentes": presentes,
            "demoras": demoras,
            "ausentes": ausentes,
            "porcentaje": porcentaje

        })
    

    conn.close()

    return render_template(
        "reporte_resultado.html",
        reporte=reporte,
        mes=mes,
        dias_habiles=dias_habiles
    )
# =========================
# EXPORTAR REPORTE WORD
# =========================
@app.route("/reportes/word", methods=["POST"])
def reporte_word():

    if "docente_id" not in session:
        return redirect("/login")

    grado_nombre = request.form["grado_nombre"]
    escuela_nombre = request.form["escuela_nombre"]
    mes = request.form["mes"]
    dias_habiles = int(
        request.form["dias_habiles"]
    )

    conn = get_connection()
    cursor = conn.cursor()

    grado_id = request.form["grado_id"]

    
    cursor.execute("""
    SELECT *
    FROM alumnos
    WHERE grado_id = %s
    AND activo = 1
    ORDER BY apellido ASC
    """, (grado_id,))

    alumnos = cursor.fetchall()

    # =========================
    # CREAR WORD
    # =========================
    doc = Document()

    # TITULO
    titulo = doc.add_heading(
        "REPORTE MENSUAL DE ASISTENCIA",
        level=1
    )

    doc.add_paragraph(
        f"{escuela_nombre}"
    )

    doc.add_paragraph(
        f"{grado_nombre}"
    )

    doc.add_paragraph(
        f"Mes: {mes}"
    )

    # INTRO
    doc.add_paragraph(
        "Según los datos registrados "
        "en el sistema de asistencia, "
        "se obtuvieron los siguientes "
        "porcentajes correspondientes "
        "al período seleccionado."
    )

    # TABLA
    table = doc.add_table(
        rows=1,
        cols=5
    )

    table.style = "Table Grid"

    hdr = table.rows[0].cells

    hdr[0].text = "Alumno"
    hdr[1].text = "Presentes"
    hdr[2].text = "Ausentes"
    hdr[3].text = "Demoras"
    hdr[4].text = "%"

    for alumno in alumnos:

        # Presentes
        cursor.execute("""
        SELECT COUNT(*) as total
        FROM asistencias
        WHERE alumno_id = %s
        AND estado = 'Presente'
        AND fecha LIKE %s
        """, (
            alumno["id"],
            f"{mes}%"
        ))

        presentes = cursor.fetchone()["total"]

        # Ausentes
        cursor.execute("""
        SELECT COUNT(*) as total
        FROM asistencias
        WHERE alumno_id = %s
        AND estado = 'Ausente'
        AND fecha LIKE %s
        """, (
            alumno["id"],
            f"{mes}%"
        ))

        ausentes = cursor.fetchone()["total"]

        # Demoras
        cursor.execute("""
        SELECT COUNT(*) as total
        FROM asistencias
        WHERE alumno_id = %s
        AND estado = 'Demora'
        AND fecha LIKE %s
        """, (
            alumno["id"],
            f"{mes}%"
        ))

        demoras = cursor.fetchone()["total"]

        porcentaje = round(
            (
                (presentes + demoras)
                / dias_habiles
            ) * 100,
            1
        )

        row = table.add_row().cells

        row[0].text = (
            f"{alumno['apellido']}, "
            f"{alumno['nombre']}"
        )

        row[1].text = str(presentes)
        row[2].text = str(ausentes)
        row[3].text = str(demoras)
        row[4].text = f"{porcentaje}%"

    # CIERRE
    doc.add_paragraph("")
    doc.add_paragraph(
        "Los datos reflejan el seguimiento "
        "mensual de asistencia de los alumnos."
    )

    doc.add_paragraph("")
    doc.add_paragraph("")
    doc.add_paragraph(
        "__________________________"
    )

    doc.add_paragraph(
        "Firma del docente"
    )

    # GUARDAR
    filename = (
        f"reporte_{grado_id}_{mes}.docx"
    )

    filepath = os.path.join(
        "static/reportes",
        filename
    )

    doc.save(filepath)

    conn.close()

    return redirect(
        f"/static/reportes/{filename}"
    )


# =========================
# FICHA DE SEGUIMIENTO INDIVIDUAL (Carga y Guardado)
# =========================
@app.route("/seguimiento/<int:alumno_id>", methods=["GET", "POST"])
def seguimiento_alumno(alumno_id):
    if "docente_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()
    ph = "%s" if DATABASE_URL else "?"

    if request.method == "POST":
        # 1. Captura de datos enviados desde el formulario
        mes = request.form.get("mes")
        grado_id = request.form.get("grado_id")

        asistencias_s1 = request.form.get("asistencias_s1", 0)
        asistencias_s2 = request.form.get("asistencias_s2", 0)
        asistencias_s3 = request.form.get("asistencias_s3", 0)
        asistencias_s4 = request.form.get("asistencias_s4", 0)

        inasistencias_s1 = request.form.get("inasistencias_s1", 0)
        inasistencias_s2 = request.form.get("inasistencias_s2", 0)
        inasistencias_s3 = request.form.get("inasistencias_s3", 0)
        inasistencias_s4 = request.form.get("inasistencias_s4", 0)

        tardanzas_s1 = request.form.get("tardanzas_s1", 0)
        tardanzas_s2 = request.form.get("tardanzas_s2", 0)
        tardanzas_s3 = request.form.get("tardanzas_s3", 0)
        tardanzas_s4 = request.form.get("tardanzas_s4", 0)

        obs_s1 = request.form.get("obs_s1", "")
        obs_s2 = request.form.get("obs_s2", "")
        obs_s3 = request.form.get("obs_s3", "")
        obs_s4 = request.form.get("obs_s4", "")

        participacion = request.form.get("participacion")
        entrega_tareas = request.form.get("entrega_tareas")
        comprension_contenidos = request.form.get("comprension_contenidos")

        respeta_normas = request.form.get("respeta_normas")
        trabaja_en_equipo = request.form.get("trabaja_en_equipo")
        mantiene_respeto = request.form.get("mantiene_respeto")

        observaciones_generales = request.form.get("observaciones_generales")
        firma_base64 = request.form.get("firma_base64")

        # 2. Inserción en la base de datos
        cursor.execute(f"""
            INSERT INTO seguimientos (
                alumno_id, grado_id, docente_id, mes,
                asistencias_s1, asistencias_s2, asistencias_s3, asistencias_s4,
                inasistencias_s1, inasistencias_s2, inasistencias_s3, inasistencias_s4,
                tardanzas_s1, tardanzas_s2, tardanzas_s3, tardanzas_s4,
                obs_s1, obs_s2, obs_s3, obs_s4,
                participacion, entrega_tareas, comprension_contenidos,
                respeta_normas, trabaja_en_equipo, mantiene_respeto,
                observaciones_generales, firma_base64
            ) VALUES (
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph},
                {ph}, {ph}, {ph},
                {ph}, {ph}
            )
        """, (
            alumno_id, grado_id, session["docente_id"], mes,
            asistencias_s1, asistencias_s2, asistencias_s3, asistencias_s4,
            inasistencias_s1, inasistencias_s2, inasistencias_s3, inasistencias_s4,
            tardanzas_s1, tardanzas_s2, tardanzas_s3, tardanzas_s4,
            obs_s1, obs_s2, obs_s3, obs_s4,
            participacion, entrega_tareas, comprension_contenidos,
            respeta_normas, trabaja_en_equipo, mantiene_respeto,
            observaciones_generales, firma_base64
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("seguimiento_inicio", grado_id=grado_id))

    # GET: Obtener datos del alumno con su escuela y grado asignado
    cursor.execute(f"""
        SELECT 
            a.id, 
            a.nombre, 
            a.apellido, 
            a.grado_id,
            g.nombre AS grado_nombre,
            e.nombre AS escuela_nombre
        FROM alumnos a
        LEFT JOIN grados g ON a.grado_id = g.id
        LEFT JOIN escuelas e ON g.escuela_id = e.id
        WHERE a.id = {ph}
    """, (alumno_id,))
    
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Alumno no encontrado", 404

    # Formateo como diccionario para compatibilidad con la notación de punto en Jinja2
    if isinstance(row, dict):
        alumno = row
    else:
        alumno = {
            "id": row[0],
            "nombre": row[1],
            "apellido": row[2],
            "grado_id": row[3],
            "grado_nombre": row[4],
            "escuela_nombre": row[5]
        }

    return render_template("seguimiento_alumno.html", alumno=alumno)

@app.route("/alumnos/carga-masiva-ia", methods=["POST"])
def carga_masiva_ia():
    if "docente_id" not in session:
        return redirect("/login")

    escuela_id = request.form.get("escuela_id")
    grado_id = request.form.get("grado_id")
    archivo = request.files.get("archivo")

    if not archivo or not grado_id:
        return "Error: Debe seleccionar un grado y subir un archivo válido.", 400

    # Crear carpeta temporal de subidas si no existe
    upload_dir = os.path.join(app.root_path, "static", "uploads_temp")
    os.makedirs(upload_dir, exist_ok=True)

    # Guardar el archivo recibido temporalmente
    temp_filepath = os.path.join(upload_dir, secrets.token_hex(8) + "_" + archivo.filename)
    archivo.save(temp_filepath)

    try:
        # Llamar a la función con IA de Gemini
        alumnos_extraidos = procesar_documento_alumnos(temp_filepath)

        # Eliminar el archivo temporal local
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        # Renderizar la plantilla de revisión con la lista extraída
        return render_template(
            "confirmar_alumnos_ia.html",
            alumnos=alumnos_extraidos,
            escuela_id=escuela_id,
            grado_id=grado_id
        )

    except Exception as e:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return f"Ocurrió un error al analizar el documento con la IA: {str(e)}", 500
@app.route("/alumnos/guardar-masivo", methods=["POST"])
def guardar_masivo():
    if "docente_id" not in session:
        return redirect("/login")

    grado_id = request.form.get("grado_id")
    
    # Obtenemos las listas de campos enviados desde el formulario editable
    nombres = request.form.getlist("nombre[]")
    apellidos = request.form.getlist("apellido[]")
    sexos = request.form.getlist("sexo[]")

    if not nombres or not grado_id:
        return redirect("/alumnos")

    conn = get_connection()
    cursor = conn.cursor()

    for i in range(len(nombres)):
        nom = nombres[i].strip()
        ape = apellidos[i].strip()
        sex = sexos[i].strip()

        # Si el usuario dejó la fila vacía en la tabla, la omitimos
        if not nom or not ape:
            continue

        # Generar un token único irrepetible para el código QR del alumno
        qr_token = secrets.token_hex(16)

        cursor.execute("""
            INSERT INTO alumnos (nombre, apellido, sexo, grado_id, qr_token)
            VALUES (%s, %s, %s, %s, %s)
        """, (nom, ape, sex, int(grado_id), qr_token))

    conn.commit()
    conn.close()

    # Redirigir al listado de alumnos del grado correspondiente
    return redirect(f"/alumnos?grado_id={grado_id}")
    
    

# =========================
# SELECCIÓN Y FILTRO DE SEGUIMIENTO (Pantalla Previa)
# =========================
@app.route("/seguimiento/seleccion", methods=["GET"])
def seguimiento_seleccion():
    if "docente_id" not in session:
        return redirect("/login")

    # Captura de parámetros GET para los filtros
    escuela_id = request.args.get("escuela_id", type=int)
    grado_id = request.args.get("grado_id", type=int)

    conn = get_connection()
    cursor = conn.cursor()
    ph = "%s" if DATABASE_URL else "?"

    # 1. Obtener todas las escuelas (sin filtrar por docente_id directamente en escuelas)
    cursor.execute("SELECT id, nombre, numero FROM escuelas ORDER BY nombre")
    escuelas = cursor.fetchall()

    grados = []
    alumnos = []

    # 2. Si hay escuela elegida, obtener sus grados
    if escuela_id:
        cursor.execute(f"SELECT id, nombre FROM grados WHERE escuela_id = {ph} ORDER BY nombre", (escuela_id,))
        grados = cursor.fetchall()

    # 3. Si hay grado elegido, obtener los alumnos correspondientes
    if grado_id:
        cursor.execute(f"SELECT id, apellido, nombre, dni FROM alumnos WHERE grado_id = {ph} ORDER BY apellido, nombre", (grado_id,))
        alumnos = cursor.fetchall()

    conn.close()

    return render_template(
        "seguimiento_seleccion.html",
        escuelas=escuelas,
        grados=grados,
        alumnos=alumnos,
        escuela_id=escuela_id,
        grado_id=grado_id
    )

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():

    if "docente_id" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        nombre=session["docente_nombre"]
    )


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )