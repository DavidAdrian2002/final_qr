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

    conn.commit()

    conn.close()