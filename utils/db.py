import os

# =========================
# DETECTAR ENTORNO
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    print("USANDO POSTGRESQL")
else:
    print("USANDO SQLITE")

# =========================
# POSTGRESQL (RENDER)
# =========================
if DATABASE_URL:

    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Fix Render
    if DATABASE_URL.startswith("postgres://"):

        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

    def get_connection():

        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

# =========================
# SQLITE (LOCAL)
# =========================
else:

    import sqlite3

    DATABASE = "database.db"

    def get_connection():

        conn = sqlite3.connect(DATABASE)

        conn.row_factory = sqlite3.Row

        return conn


# =========================
# INIT DB
# =========================
def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    # Detectar placeholders
    placeholder = "%s" if DATABASE_URL else "?"

    # =========================
    # DOCENTES
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docentes (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # =========================
    # ESCUELAS
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS escuelas (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        numero TEXT,
        localidad TEXT
    )
    """)

    # =========================
    # GRADOS
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grados (
        id SERIAL PRIMARY KEY,

        nombre TEXT NOT NULL,

        escuela_id INTEGER NOT NULL,

        FOREIGN KEY(escuela_id)
        REFERENCES escuelas(id)
    )
    """)

    # =========================
    # ALUMNOS
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id SERIAL PRIMARY KEY,

        nombre TEXT NOT NULL,

        apellido TEXT NOT NULL,

        dni TEXT,

        sexo TEXT NOT NULL,

        foto TEXT,

        qr_token TEXT UNIQUE,

        activo INTEGER DEFAULT 1,

        grado_id INTEGER NOT NULL,

        FOREIGN KEY(grado_id)
        REFERENCES grados(id)
    )
    """)

    # =========================
    # ASISTENCIAS
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id SERIAL PRIMARY KEY,

        alumno_id INTEGER NOT NULL,

        fecha TEXT NOT NULL,

        hora TEXT NOT NULL,

        estado TEXT NOT NULL,

        grado_id INTEGER NOT NULL,

        FOREIGN KEY(alumno_id)
        REFERENCES alumnos(id),

        FOREIGN KEY(grado_id)
        REFERENCES grados(id)
    )
    """)

    # =========================
    # DOCENTE ESCUELAS
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docente_escuelas (
        id SERIAL PRIMARY KEY,

        docente_id INTEGER NOT NULL,

        escuela_id INTEGER NOT NULL,

        FOREIGN KEY(docente_id)
        REFERENCES docentes(id),

        FOREIGN KEY(escuela_id)
        REFERENCES escuelas(id)
    )
    """)
    # =========================
    # SEGUIMIENTOS DE ALUMNOS
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seguimientos_alumnos (
        id SERIAL PRIMARY KEY,

        alumno_id INTEGER NOT NULL,
        docente_id INTEGER NOT NULL,
        mes TEXT NOT NULL,

        -- Asistencia (Semanas 1 a 4)
        asistencias_s1 INTEGER DEFAULT 0, inasistencias_s1 INTEGER DEFAULT 0, tardanzas_s1 INTEGER DEFAULT 0, obs_s1 TEXT,
        asistencias_s2 INTEGER DEFAULT 0, inasistencias_s2 INTEGER DEFAULT 0, tardanzas_s2 INTEGER DEFAULT 0, obs_s2 TEXT,
        asistencias_s3 INTEGER DEFAULT 0, inasistencias_s3 INTEGER DEFAULT 0, tardanzas_s3 INTEGER DEFAULT 0, obs_s3 TEXT,
        asistencias_s4 INTEGER DEFAULT 0, inasistencias_s4 INTEGER DEFAULT 0, tardanzas_s4 INTEGER DEFAULT 0, obs_s4 TEXT,

        -- Desempeño Académico
        participacion TEXT,
        entrega_tareas TEXT,
        comprension_contenidos TEXT,

        -- Conducta y Convivencia
        respeta_normas TEXT,
        trabaja_en_equipo TEXT,
        mantiene_respeto TEXT,

        -- Observaciones y Firma
        observaciones_generales TEXT,
        firma_base64 TEXT,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(alumno_id) REFERENCES alumnos(id),
        FOREIGN KEY(docente_id) REFERENCES docentes(id)
    )
    """)
    # =========================
    # EVENTOS Y NOTAS DEL CALENDARIO
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos_calendario (
        id SERIAL PRIMARY KEY,
        docente_id INTEGER NOT NULL,
        escuela_id INTEGER,
        grado_id INTEGER,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        fecha TEXT NOT NULL,          -- Formato YYYY-MM-DD
        tipo TEXT DEFAULT 'nota',     -- 'examen', 'evento', 'reunion', 'informe', 'nota'
        color TEXT DEFAULT '#3b82f6',  -- Para diferenciar visualmente en el calendario
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(docente_id) REFERENCES docentes(id) ON DELETE CASCADE,
        FOREIGN KEY(escuela_id) REFERENCES escuelas(id) ON DELETE SET NULL,
        FOREIGN KEY(grado_id) REFERENCES grados(id) ON DELETE SET NULL
    )
    """)
    # Asegurar campos adicionales para la credencial en la tabla docentes
    cursor.execute("""
        ALTER TABLE docentes ADD COLUMN IF NOT EXISTS foto TEXT DEFAULT '/static/uploads/default-avatar.png';
        ALTER TABLE docentes ADD COLUMN IF NOT EXISTS dni TEXT;
        ALTER TABLE docentes ADD COLUMN IF NOT EXISTS legajo TEXT;
        ALTER TABLE docentes ADD COLUMN IF NOT EXISTS titulo TEXT DEFAULT 'Docente Nivel Primario';
    """)

    conn.commit()

    conn.close()