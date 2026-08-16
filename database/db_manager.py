"""
db_manager.py
-------------
Capa de acceso a datos para la aplicación 'Control de Acceso Gym'.

Usa sqlite3 (librería estándar de Python) para gestionar el archivo
gym_data.db ubicado en la raíz del proyecto. Si el archivo no existe,
se crea automáticamente en la primera ejecución.

Funciones principales
─────────────────────
  init_db()          → Crea las tablas si no existen. Llamar al inicio de la app.
  get_connection()   → Retorna una conexión configurada lista para usar.

Convenciones de uso
───────────────────
  - Siempre usar get_connection() para obtener conexiones.
  - Cerrar la conexión en un bloque try/finally o con `with get_connection() as conn`.
  - Las llaves foráneas están activadas en cada conexión (PRAGMA foreign_keys = ON).
  - Las columnas DATETIME se almacenan como texto ISO-8601: 'YYYY-MM-DD HH:MM:SS'.

Tablas creadas
──────────────
  clientes, huellas, planes, membresias,
  ingresos_biometricos, aperturas_manuales,
  configuracion

Ejemplo de uso:
    from database.db_manager import get_connection, init_db

    init_db()   # garantiza que las tablas existen

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clientes")
        rows = cur.fetchall()
"""

import sqlite3
import pathlib

# ── Ruta al archivo de base de datos ─────────────────────────────────────────
# Se coloca en la raíz del proyecto (carpeta padre de database/).
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_PATH       = _PROJECT_ROOT / "gym_data.db"


# ── Sentencias DDL ────────────────────────────────────────────────────────────
_DDL_STATEMENTS = [

    # ── clientes ──────────────────────────────────────────────────
    # Datos personales del miembro del gimnasio.
    # cedula tiene restricción UNIQUE para evitar duplicados.
    """
    CREATE TABLE IF NOT EXISTS clientes (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        cedula           TEXT    NOT NULL UNIQUE,
        nombre           TEXT    NOT NULL,
        telefono         TEXT,
        fecha_registro   DATETIME NOT NULL
                             DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
    )
    """,

    # ── huellas ───────────────────────────────────────────────────
    # Plantillas biométricas asociadas a un cliente.
    # La columna 'plantilla' almacena los bytes del SDK en BASE-64.
    # La columna 'dedo' indica cuál dedo se enroló (ej. 'índice_derecho').
    """
    CREATE TABLE IF NOT EXISTS huellas (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id  INTEGER NOT NULL
                        REFERENCES clientes(id) ON DELETE CASCADE,
        dedo        TEXT    NOT NULL,
        plantilla   TEXT    NOT NULL
    )
    """,

    # ── planes ────────────────────────────────────────────────────
    # Catálogo de membresías disponibles en el gimnasio.
    """
    CREATE TABLE IF NOT EXISTS planes (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre         TEXT    NOT NULL,
        precio         REAL    NOT NULL DEFAULT 0.0,
        dias_duracion  INTEGER NOT NULL DEFAULT 30
    )
    """,

    # ── membresias ────────────────────────────────────────────────
    # Relación entre un cliente y el plan contratado.
    # estado: 'ACTIVA' | 'VENCIDA' | 'SUSPENDIDA'
    """
    CREATE TABLE IF NOT EXISTS membresias (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id        INTEGER NOT NULL
                              REFERENCES clientes(id) ON DELETE CASCADE,
        plan_id           INTEGER NOT NULL
                              REFERENCES planes(id) ON DELETE RESTRICT,
        fecha_inicio      DATE    NOT NULL,
        fecha_vencimiento DATE    NOT NULL,
        estado            TEXT    NOT NULL DEFAULT 'ACTIVA'
                              CHECK (estado IN ('ACTIVA', 'VENCIDA', 'SUSPENDIDA')),
        dias_restantes_congelados INTEGER DEFAULT 0,
        fecha_inicio_congelamiento DATE,
        fecha_fin_congelamiento DATE
    )
    """,

    # ── ingresos_biometricos ──────────────────────────────────────
    # Log de cada ingreso verificado por huella dactilar.
    """
    CREATE TABLE IF NOT EXISTS ingresos_biometricos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id  INTEGER NOT NULL
                        REFERENCES clientes(id) ON DELETE CASCADE,
        fecha_hora  DATETIME NOT NULL
                        DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
    )
    """,

    # ── aperturas_manuales ────────────────────────────────────────
    # Registro de cada apertura manual con su justificación.
    # No referencia a cliente porque puede haber aperturas sin cliente en sistema.
    """
    CREATE TABLE IF NOT EXISTS aperturas_manuales (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        justificacion TEXT     NOT NULL,
        fecha_hora    DATETIME NOT NULL
                          DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
    )
    """,

    # ── historial_congelaciones ───────────────────────────────────
    # Registro de acciones de congelamiento y reactivación de membresías.
    """
    CREATE TABLE IF NOT EXISTS historial_congelaciones (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        membresia_id  INTEGER NOT NULL REFERENCES membresias(id) ON DELETE CASCADE,
        fecha         DATE NOT NULL DEFAULT (STRFTIME('%Y-%m-%d', 'now', 'localtime')),
        justificacion TEXT,
        accion        TEXT NOT NULL CHECK (accion IN ('CONGELADA', 'REACTIVADA'))
    )
    """,

    # ── configuracion ─────────────────────────────────────────────
    # Tabla genérica clave-valor para ajustes del sistema.
    # Clave 'puerto_com_torniquete' → nombre del puerto COM (ej. 'COM3').
    """
    CREATE TABLE IF NOT EXISTS configuracion (
        clave  TEXT PRIMARY KEY,
        valor  TEXT NOT NULL DEFAULT ''
    )
    """,

    # ── Índices para consultas frecuentes ─────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_membresias_cliente   ON membresias(cliente_id)",
    "CREATE INDEX IF NOT EXISTS idx_membresias_estado    ON membresias(estado)",
    "CREATE INDEX IF NOT EXISTS idx_ingresos_cliente     ON ingresos_biometricos(cliente_id)",
    "CREATE INDEX IF NOT EXISTS idx_ingresos_fecha       ON ingresos_biometricos(fecha_hora)",
    "CREATE INDEX IF NOT EXISTS idx_aperturas_fecha      ON aperturas_manuales(fecha_hora)",
]


def get_connection() -> sqlite3.Connection:
    """
    Abre y retorna una conexión a la base de datos gym_data.db.

    Configuración aplicada en cada conexión:
      - row_factory = sqlite3.Row  → acceso a columnas por nombre (row['cedula'])
      - PRAGMA foreign_keys = ON   → valida integridad referencial en cada operación
      - PRAGMA journal_mode = WAL  → escrituras concurrentes más seguras

    Returns:
        sqlite3.Connection: Conexión lista para usar.

    Example:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM clientes WHERE cedula = ?", (cedula,))
            cliente = cur.fetchone()
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("PRAGMA journal_mode = WAL;")

    return conn


def obtener_historial_ingresos_rango(fecha_inicio: str, fecha_fin: str) -> list[dict]:
    """
    Obtiene el historial de ingresos de personas en un rango de fechas.
    Fechas en formato YYYY-MM-DD.
    """
    QUERY = """
        SELECT
            ib.fecha_hora, c.cedula, c.nombre
        FROM ingresos_biometricos ib
        JOIN clientes c ON ib.cliente_id = c.id
        WHERE date(ib.fecha_hora) BETWEEN ? AND ?
        ORDER BY ib.fecha_hora DESC
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY, (fecha_inicio, fecha_fin))
        return [dict(r) for r in cur.fetchall()]

def obtener_historial_pagos_rango(fecha_inicio: str, fecha_fin: str) -> list[dict]:
    """
    Obtiene el historial de pagos de membresías en un rango de fechas.
    Fechas en formato YYYY-MM-DD.
    """
    QUERY = """
        SELECT
            m.fecha_inicio, c.cedula, c.nombre AS cliente_nombre, p.nombre AS plan_nombre, p.precio
        FROM membresias m
        JOIN clientes c ON m.cliente_id = c.id
        JOIN planes p ON m.plan_id = p.id
        WHERE date(m.fecha_inicio) BETWEEN ? AND ?
        ORDER BY m.fecha_inicio DESC
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY, (fecha_inicio, fecha_fin))
        return [dict(r) for r in cur.fetchall()]


def init_db() -> None:
    """
    Inicializa la base de datos: crea el archivo y todas las tablas si no existen.

    Es idempotente: puede llamarse múltiples veces sin efectos secundarios
    (todas las sentencias usan CREATE TABLE IF NOT EXISTS).

    Llamar UNA VEZ al iniciar la aplicación (antes de montar la UI de Flet).

    Raises:
        sqlite3.Error: Si hay un problema de permisos o disco lleno.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        for statement in _DDL_STATEMENTS:
            cur.execute(statement)
            
        # Migración para la tabla membresias
        try:
            cur.execute("ALTER TABLE membresias ADD COLUMN dias_restantes_congelados INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        try:
            cur.execute("ALTER TABLE membresias ADD COLUMN fecha_inicio_congelamiento DATE")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE membresias ADD COLUMN fecha_fin_congelamiento DATE")
        except sqlite3.OperationalError:
            pass
        conn.commit()

    print(f"[DB] Base de datos lista en: {DB_PATH}")


# ── Utilidades de diagnóstico ─────────────────────────────────────────────────

def get_db_info() -> dict:
    """
    Retorna un diccionario con información básica de la BD.
    Útil para la vista de Configuración o logs de diagnóstico.

    Returns:
        dict con claves: 'path', 'version', 'tablas'
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT sqlite_version()")
        version = cur.fetchone()[0]

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tablas = [row[0] for row in cur.fetchall()]

    return {
        "path":    str(DB_PATH),
        "version": version,
        "tablas":  tablas,
    }


# ── Ejecución directa para pruebas ────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    info = get_db_info()
    print(f"SQLite versión : {info['version']}")
    print(f"Tablas creadas : {', '.join(info['tablas'])}")


# ════════════════════════════════════════════════════════════════════════════════
# PLANES — CRUD
# ════════════════════════════════════════════════════════════════════════════════

def crear_plan(nombre: str, precio: float, dias: int) -> int:
    """
    Inserta un nuevo plan en el catálogo.

    Args:
        nombre: Nombre descriptivo del plan (ej. 'Mensual').
        precio: Costo en moneda local (ej. 350.0).
        dias:   Duración en días (ej. 30).

    Returns:
        int: ID (rowid) del plan recién creado.

    Raises:
        sqlite3.IntegrityError: Si el nombre ya existe (agregar UNIQUE al DDL si se desea).
        sqlite3.Error: Ante cualquier otro fallo de BD.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO planes (nombre, precio, dias_duracion) VALUES (?, ?, ?)",
            (nombre, float(precio), int(dias)),
        )
        conn.commit()
        return cur.lastrowid


def obtener_planes() -> list[sqlite3.Row]:
    """
    Retorna todos los planes ordenados por nombre.

    Returns:
        list[sqlite3.Row]: Cada fila tiene columnas accesibles por nombre:
                           row['id'], row['nombre'], row['precio'], row['dias_duracion']
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, precio, dias_duracion FROM planes ORDER BY nombre")
        return cur.fetchall()


def eliminar_plan(plan_id: int) -> None:
    """
    Elimina un plan por su ID.

    Args:
        plan_id: ID del plan a eliminar.

    Raises:
        sqlite3.IntegrityError: Si hay membresías activas vinculadas a este plan
                                (ON DELETE RESTRICT en la FK de membresías).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM planes WHERE id = ?", (plan_id,))
        conn.commit()


# ════════════════════════════════════════════════════════════════════════════════
# CLIENTES — CRUD
# ════════════════════════════════════════════════════════════════════════════════

def crear_cliente(cedula: str, nombre: str, telefono: str = "") -> int:
    """
    Registra un nuevo cliente en la base de datos.

    La fecha de registro se establece automáticamente con la hora local actual.

    Args:
        cedula:   Número de cédula / DNI. Debe ser único.
        nombre:   Nombre completo del cliente.
        telefono: Teléfono de contacto (opcional).

    Returns:
        int: ID del cliente recién creado.

    Raises:
        sqlite3.IntegrityError: Si ya existe un cliente con esa cédula.
        sqlite3.Error: Ante cualquier otro fallo de BD.
    """
    from datetime import datetime
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (cedula, nombre, telefono, fecha_registro) VALUES (?, ?, ?, ?)",
            (cedula.strip(), nombre.strip(), telefono.strip(), fecha),
        )
        conn.commit()
        return cur.lastrowid


def obtener_clientes() -> list[dict]:
    """
    Retorna todos los clientes ordenados por nombre, incluyendo
    su plan actual y días restantes si tienen una membresía activa.

    Returns:
        list[dict]: Lista de diccionarios con la información del cliente.
    """
    import sqlite3
    from datetime import datetime

    QUERY = """
        SELECT 
            c.id, c.cedula, c.nombre, c.telefono, c.fecha_registro,
            p.nombre AS plan_actual,
            m.fecha_vencimiento
        FROM clientes c
        LEFT JOIN (
            SELECT cliente_id, plan_id, fecha_vencimiento
            FROM membresias
            WHERE estado = 'ACTIVA'
            GROUP BY cliente_id
            HAVING MAX(id)
        ) m ON c.id = m.cliente_id
        LEFT JOIN planes p ON m.plan_id = p.id
        ORDER BY c.nombre
    """
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY)
        filas = cur.fetchall()

    hoy = datetime.now().date()
    resultados = []
    
    for fila in filas:
        cliente = dict(fila)
        if cliente["fecha_vencimiento"]:
            fv = datetime.strptime(cliente["fecha_vencimiento"], "%Y-%m-%d").date()
            dias_restantes = (fv - hoy).days
            cliente["dias_restantes"] = dias_restantes if dias_restantes >= 0 else 0
        else:
            cliente["plan_actual"] = "Sin plan"
            cliente["dias_restantes"] = 0
            
        resultados.append(cliente)

    return resultados


def buscar_clientes(query: str) -> list[dict]:
    """
    Busca clientes cuyo nombre o cédula contengan el texto dado,
    incluyendo su plan actual y días restantes.

    Args:
        query: Texto a buscar (insensible a mayúsculas).

    Returns:
        list[dict]: Clientes que coinciden, ordenados por nombre.
    """
    import sqlite3
    from datetime import datetime
    
    pattern = f"%{query}%"
    QUERY = """
        SELECT 
            c.id, c.cedula, c.nombre, c.telefono, c.fecha_registro,
            p.nombre AS plan_actual,
            m.fecha_vencimiento
        FROM clientes c
        LEFT JOIN (
            SELECT cliente_id, plan_id, fecha_vencimiento
            FROM membresias
            WHERE estado = 'ACTIVA'
            GROUP BY cliente_id
            HAVING MAX(id)
        ) m ON c.id = m.cliente_id
        LEFT JOIN planes p ON m.plan_id = p.id
        WHERE c.nombre LIKE ? OR c.cedula LIKE ?
        ORDER BY c.nombre
    """
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY, (pattern, pattern))
        filas = cur.fetchall()

    hoy = datetime.now().date()
    resultados = []
    
    for fila in filas:
        cliente = dict(fila)
        if cliente["fecha_vencimiento"]:
            fv = datetime.strptime(cliente["fecha_vencimiento"], "%Y-%m-%d").date()
            dias_restantes = (fv - hoy).days
            cliente["dias_restantes"] = dias_restantes if dias_restantes >= 0 else 0
        else:
            cliente["plan_actual"] = "Sin plan"
            cliente["dias_restantes"] = 0
            
        resultados.append(cliente)

    return resultados

def actualizar_cliente(cliente_id: int, cedula: str, nombre: str, telefono: str) -> None:
    """
    Actualiza la información de un cliente existente.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE clientes SET cedula = ?, nombre = ?, telefono = ? WHERE id = ?",
            (cedula.strip(), nombre.strip(), telefono.strip(), cliente_id)
        )
        conn.commit()

def eliminar_cliente(cliente_id: int) -> None:
    """
    Elimina un cliente y sus registros dependientes (CASCADE).

    Args:
        cliente_id: ID del cliente a eliminar.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()


# ════════════════════════════════════════════════════════════════════════════════
# MEMBRESÍAS Y RENOVACIONES
# ════════════════════════════════════════════════════════════════════════════════

def obtener_clientes_para_dropdown() -> list[dict]:
    """
    Retorna una lista de diccionarios ligeros con id, cedula y nombre.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, cedula, nombre FROM clientes ORDER BY nombre")
        return [dict(row) for row in cur.fetchall()]


def crear_membresia(cliente_id: int, plan_id: int, fecha_inicio: str = None) -> dict:
    """
    Crea una membresía activa calculando las fechas según el plan y una fecha de inicio opcional.

    Args:
        cliente_id: ID del cliente.
        plan_id: ID del plan.
        fecha_inicio: Fecha de inicio opcional (YYYY-MM-DD). Si es None, usa hoy.

    Returns:
        dict: Detalles de la membresía creada (incluyendo fecha de vencimiento).
    """
    from datetime import datetime, timedelta

    with get_connection() as conn:
        cur = conn.cursor()
        
        # a. Consultar los días de duración del plan
        cur.execute("SELECT dias_duracion FROM planes WHERE id = ?", (plan_id,))
        row_plan = cur.fetchone()
        if not row_plan:
            raise ValueError("Plan no encontrado")
        
        dias_duracion = row_plan["dias_duracion"]

        # b. Calcular fecha_inicio
        if fecha_inicio is None:
            fecha_inicio_obj = datetime.now().date()
            fecha_inicio = fecha_inicio_obj.strftime("%Y-%m-%d")
        else:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()

        # c. Calcular fecha_vencimiento
        fecha_vencimiento_obj = fecha_inicio_obj + timedelta(days=dias_duracion)
        fecha_vencimiento = fecha_vencimiento_obj.strftime("%Y-%m-%d")

        # d. Insertar registro en membresias
        cur.execute(
            """
            INSERT INTO membresias (cliente_id, plan_id, fecha_inicio, fecha_vencimiento, estado)
            VALUES (?, ?, ?, ?, 'ACTIVA')
            """,
            (cliente_id, plan_id, fecha_inicio, fecha_vencimiento)
        )
        conn.commit()
        
        return {
            "id": cur.lastrowid,
            "fecha_inicio": fecha_inicio,
            "fecha_vencimiento": fecha_vencimiento,
            "estado": "ACTIVA"
        }

def programar_congelamiento(membresia_id: int, justificacion: str, fecha_inicio: str, fecha_fin: str = None) -> None:
    """
    Programa el congelamiento de una membresía.
    Si fecha_inicio es hoy o en el pasado, la suspende inmediatamente.
    """
    from datetime import datetime
    with get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT fecha_vencimiento, estado FROM membresias WHERE id = ?", (membresia_id,))
        row = cur.fetchone()
        
        if not row:
            raise ValueError("Membresía no encontrada.")
        if row["estado"] not in ("ACTIVA", "SUSPENDIDA"):
            raise ValueError(f"No se puede programar en estado {row['estado']}.")
            
        fecha_vencimiento_obj = datetime.strptime(row["fecha_vencimiento"], "%Y-%m-%d").date()
        fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        hoy = datetime.now().date()
        
        dias_restantes = (fecha_vencimiento_obj - fecha_inicio_obj).days
        if dias_restantes < 0:
            raise ValueError("La fecha de inicio programada es posterior al vencimiento de la membresía.")
            
        nuevo_estado = "SUSPENDIDA" if fecha_inicio_obj <= hoy else row["estado"]
        
        cur.execute(
            """
            UPDATE membresias 
            SET estado = ?, dias_restantes_congelados = ?, 
                fecha_inicio_congelamiento = ?, fecha_fin_congelamiento = ?
            WHERE id = ?
            """,
            (nuevo_estado, dias_restantes, fecha_inicio, fecha_fin, membresia_id)
        )
        
        cur.execute(
            """
            INSERT INTO historial_congelaciones (membresia_id, justificacion, accion)
            VALUES (?, ?, 'CONGELADA')
            """,
            (membresia_id, justificacion)
        )
        conn.commit()


def reactivar_membresia(membresia_id: int) -> dict:
    """
    Reactivar una membresía congelada, calculando nueva fecha de vencimiento.
    """
    from datetime import datetime, timedelta
    with get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT dias_restantes_congelados, estado FROM membresias WHERE id = ?", (membresia_id,))
        row = cur.fetchone()
        
        if not row:
            raise ValueError("Membresía no encontrada.")
        if row["estado"] != "SUSPENDIDA":
            raise ValueError(f"No se puede reactivar una membresía en estado {row['estado']}.")
            
        dias_restantes = row["dias_restantes_congelados"]
        if dias_restantes is None:
            dias_restantes = 0
            
        hoy = datetime.now().date()
        nueva_fecha_vencimiento_obj = hoy + timedelta(days=dias_restantes)
        nueva_fecha_vencimiento = nueva_fecha_vencimiento_obj.strftime("%Y-%m-%d")
        
        cur.execute(
            """
            UPDATE membresias 
            SET estado = 'ACTIVA', fecha_vencimiento = ?, dias_restantes_congelados = 0,
                fecha_inicio_congelamiento = NULL, fecha_fin_congelamiento = NULL
            WHERE id = ?
            """,
            (nueva_fecha_vencimiento, membresia_id)
        )
        
        cur.execute(
            """
            INSERT INTO historial_congelaciones (membresia_id, justificacion, accion)
            VALUES (?, 'Reactivación por el usuario', 'REACTIVADA')
            """,
            (membresia_id,)
        )
        conn.commit()
        
        return {"fecha_vencimiento": nueva_fecha_vencimiento}

def procesar_congelamientos_automaticos() -> None:
    """
    Se ejecuta al iniciar la app.
    Verifica membresías ACTIVA que deberían estar SUSPENDIDA (llegó la fecha_inicio).
    Verifica membresías SUSPENDIDA que deberían reactivarse (llegó o pasó la fecha_fin).
    """
    from datetime import datetime, timedelta
    with get_connection() as conn:
        cur = conn.cursor()
        hoy_str = datetime.now().date().strftime("%Y-%m-%d")
        
        # 1. Congelar las que llegaron a su fecha_inicio_congelamiento
        cur.execute(
            """
            UPDATE membresias
            SET estado = 'SUSPENDIDA'
            WHERE estado = 'ACTIVA' 
              AND fecha_inicio_congelamiento IS NOT NULL
              AND fecha_inicio_congelamiento <= ?
            """,
            (hoy_str,)
        )
        
        # 2. Reactivar las que llegaron a su fecha_fin_congelamiento
        cur.execute(
            """
            SELECT id, dias_restantes_congelados 
            FROM membresias
            WHERE estado = 'SUSPENDIDA' 
              AND fecha_fin_congelamiento IS NOT NULL
              AND fecha_fin_congelamiento <= ?
            """,
            (hoy_str,)
        )
        para_reactivar = cur.fetchall()
        
        hoy_obj = datetime.now().date()
        
        for row in para_reactivar:
            mid = row["id"]
            dias_restantes = row["dias_restantes_congelados"] or 0
            
            nueva_fecha_vencimiento_obj = hoy_obj + timedelta(days=dias_restantes)
            nueva_fecha_vencimiento = nueva_fecha_vencimiento_obj.strftime("%Y-%m-%d")
            
            cur.execute(
                """
                UPDATE membresias 
                SET estado = 'ACTIVA', fecha_vencimiento = ?, dias_restantes_congelados = 0,
                    fecha_inicio_congelamiento = NULL, fecha_fin_congelamiento = NULL
                WHERE id = ?
                """,
                (nueva_fecha_vencimiento, mid)
            )
            cur.execute(
                """
                INSERT INTO historial_congelaciones (membresia_id, justificacion, accion)
                VALUES (?, 'Reactivación automática', 'REACTIVADA')
                """,
                (mid,)
            )
            
        conn.commit()


def obtener_historial_membresias(busqueda: str = None) -> list[dict]:
    """
    Devuelve las últimas renovaciones usando JOIN, con opción a filtrar por cédula o nombre.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        base_query = """
            SELECT 
                m.id,
                c.nombre AS cliente_nombre,
                p.nombre AS plan_nombre,
                m.fecha_inicio,
                m.fecha_vencimiento,
                m.estado
            FROM membresias m
            JOIN clientes c ON m.cliente_id = c.id
            JOIN planes p ON m.plan_id = p.id
        """
        
        if busqueda:
            query = base_query + """
                WHERE c.cedula LIKE ? OR c.nombre LIKE ?
                ORDER BY m.id DESC
            """
            like_val = f"%{busqueda}%"
            cur.execute(query, (like_val, like_val))
        else:
            query = base_query + " ORDER BY m.id DESC LIMIT 50"
            cur.execute(query)
            
        return [dict(row) for row in cur.fetchall()]


# ════════════════════════════════════════════════════════════════════════════════
# CONTROL DE ACCESO
# ════════════════════════════════════════════════════════════════════════════════

def verificar_estado_acceso(cedula: str) -> dict:
    """
    Verifica si un cliente tiene acceso permitido (membresía activa y no vencida).
    Si tiene acceso, registra el ingreso en 'ingresos_biometricos'.

    Args:
        cedula: La cédula del cliente a verificar.

    Returns:
        dict: Resultado con el formato:
              {
                  "permitido": bool,
                  "mensaje": str,
                  "cliente_nombre": str | None,
                  "dias_restantes": int | None
              }
    """
    from datetime import datetime

    with get_connection() as conn:
        cur = conn.cursor()
        
        # a. Buscar al cliente
        cur.execute("SELECT id, nombre FROM clientes WHERE cedula = ?", (cedula.strip(),))
        cliente = cur.fetchone()
        
        if not cliente:
            return {
                "permitido": False,
                "mensaje": "Cliente no encontrado",
                "cliente_nombre": None,
                "dias_restantes": None
            }
            
        cliente_id = cliente["id"]
        cliente_nombre = cliente["nombre"]
        
        # b. Buscar la membresía activa o suspendida más reciente
        cur.execute(
            """
            SELECT id, fecha_vencimiento, estado 
            FROM membresias 
            WHERE cliente_id = ? AND estado IN ('ACTIVA', 'SUSPENDIDA')
            ORDER BY id DESC LIMIT 1
            """, 
            (cliente_id,)
        )
        membresia = cur.fetchone()
        
        if not membresia:
            return {
                "permitido": False,
                "mensaje": "No tiene membresía activa",
                "cliente_nombre": cliente_nombre,
                "dias_restantes": None
            }

        if membresia["estado"] == "SUSPENDIDA":
            return {
                "permitido": False,
                "mensaje": "Membresía Congelada",
                "cliente_nombre": cliente_nombre,
                "dias_restantes": None
            }
            
        # c. Comparar fechas
        fecha_actual = datetime.now().date()
        fecha_vencimiento = datetime.strptime(membresia["fecha_vencimiento"], "%Y-%m-%d").date()
        
        dias_restantes = (fecha_vencimiento - fecha_actual).days
        
        if dias_restantes < 0:
            # Actualizar estado si ya expiró
            cur.execute("UPDATE membresias SET estado = 'VENCIDA' WHERE id = ?", (membresia["id"],))
            conn.commit()
            return {
                "permitido": False,
                "mensaje": "Membresía vencida",
                "cliente_nombre": cliente_nombre,
                "dias_restantes": dias_restantes
            }
            
        # d. Acceso permitido, registrar ingreso
        cur.execute(
            "INSERT INTO ingresos_biometricos (cliente_id) VALUES (?)",
            (cliente_id,)
        )
        conn.commit()
        
        return {
            "permitido": True,
            "mensaje": "Acceso permitido",
            "cliente_nombre": cliente_nombre,
            "dias_restantes": dias_restantes
        }

def registrar_apertura_manual(justificacion: str) -> None:
    """
    Registra una apertura manual en la base de datos.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO aperturas_manuales (justificacion) VALUES (?)",
            (justificacion,)
        )
        conn.commit()

def obtener_aperturas_manuales(limite: int = 50) -> list[dict]:
    """
    Obtiene las últimas aperturas manuales.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT fecha_hora, justificacion FROM aperturas_manuales ORDER BY id DESC LIMIT ?",
            (limite,)
        )
        return [dict(row) for row in cur.fetchall()]

def obtener_resumen_estadisticas() -> dict:
    """
    Calcula el resumen de estadísticas diarias y generales.
    """
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Ingresos hoy
        cur.execute("SELECT COUNT(*) FROM ingresos_biometricos WHERE DATE(fecha_hora) = ?", (today_str,))
        ingresos_hoy = cur.fetchone()[0]
        
        # Recaudación hoy
        cur.execute(
            """
            SELECT COALESCE(SUM(p.precio), 0)
            FROM membresias m
            JOIN planes p ON m.plan_id = p.id
            WHERE m.fecha_inicio = ?
            """,
            (today_str,)
        )
        recaudacion_hoy = cur.fetchone()[0]
        
        # Clientes activos
        cur.execute("SELECT COUNT(DISTINCT cliente_id) FROM membresias WHERE estado = 'ACTIVA'")
        clientes_activos = cur.fetchone()[0]
        
        return {
            "ingresos_hoy": ingresos_hoy,
            "recaudacion_hoy": recaudacion_hoy,
            "clientes_activos": clientes_activos
        }


# ════════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL SISTEMA
# ════════════════════════════════════════════════════════════════════════════════

def get_config(clave: str, default: str = "") -> str:
    """
    Obtiene el valor de una clave de configuración del sistema.

    Args:
        clave:   Nombre del ajuste (ej. 'puerto_com_torniquete').
        default: Valor a retornar si la clave no existe en la BD.

    Returns:
        str: Valor almacenado, o `default` si no existe.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
        row = cur.fetchone()
        return row["valor"] if row else default


def set_config(clave: str, valor: str) -> None:
    """
    Guarda o actualiza una clave de configuración (upsert).

    Args:
        clave:  Nombre del ajuste (ej. 'puerto_com_torniquete').
        valor:  Valor a persistir   (ej. 'COM3').
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
            (clave, valor),
        )
        conn.commit()


# ════════════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN DE DATOS
# ════════════════════════════════════════════════════════════════════════════════

def exportar_ingresos_csv(ruta_archivo: str) -> int:
    """
    Exporta el historial completo de ingresos biométricos a un archivo CSV.

    El archivo resultante contiene las columnas:
        Fecha/Hora | Cédula | Nombre

    Obtiene los datos con un JOIN entre `ingresos_biometricos` y `clientes`
    para incluir la información personal del miembro en cada registro.

    Args:
        ruta_archivo: Ruta absoluta del archivo CSV a crear/sobreescribir.
                      Ejemplo: 'C:/Users/yo/Desktop/Reporte_Ingresos.csv'

    Returns:
        int: Número de filas exportadas.

    Raises:
        OSError: Si no se puede escribir en la ruta indicada.
        sqlite3.Error: Ante cualquier fallo de consulta en la BD.

    Example:
        n = exportar_ingresos_csv("C:/reportes/ingresos.csv")
        print(f"{n} registros exportados.")
    """
    import csv

    QUERY = """
        SELECT
            ib.fecha_hora   AS "Fecha/Hora",
            c.cedula        AS "Cédula",
            c.nombre        AS "Nombre"
        FROM ingresos_biometricos ib
        JOIN clientes c ON ib.cliente_id = c.id
        ORDER BY ib.fecha_hora DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY)
        filas = cur.fetchall()

    # Escribir CSV con BOM UTF-8 para que Excel lo abra correctamente
    with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=';')
        # Encabezado
        writer.writerow(["Fecha/Hora", "Cédula", "Nombre"])
        # Datos
        for fila in filas:
            writer.writerow([fila["Fecha/Hora"], fila["Cédula"], fila["Nombre"]])

    return len(filas)

def exportar_finanzas_csv(ruta_archivo: str) -> int:
    """
    Exporta el reporte financiero (ingresos por membresías) a un archivo CSV.

    El archivo resultante contiene las columnas:
        Fecha de Pago | Cédula | Cliente | Plan Adquirido | Valor Pagado

    Obtiene los datos uniendo membresias, clientes y planes.

    Args:
        ruta_archivo: Ruta absoluta del archivo CSV a crear/sobreescribir.

    Returns:
        int: Número de filas exportadas.
    """
    import csv

    QUERY = """
        SELECT
            m.fecha_inicio AS "Fecha de Pago",
            c.cedula       AS "Cédula",
            c.nombre       AS "Cliente",
            p.nombre       AS "Plan Adquirido",
            p.precio       AS "Valor Pagado"
        FROM membresias m
        JOIN clientes c ON m.cliente_id = c.id
        JOIN planes p ON m.plan_id = p.id
        ORDER BY m.fecha_inicio DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY)
        filas = cur.fetchall()

    with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Fecha de Pago", "Cédula", "Cliente", "Plan Adquirido", "Valor Pagado"])
        for fila in filas:
            writer.writerow([fila["Fecha de Pago"], fila["Cédula"], fila["Cliente"], fila["Plan Adquirido"], fila["Valor Pagado"]])

    return len(filas)


def obtener_historial_congelaciones() -> list[dict]:
    """
    Obtiene el historial de congelaciones y reactivaciones de membresías.
    """
    QUERY = """
        SELECT
            h.fecha, c.cedula, c.nombre AS cliente_nombre, h.accion, h.justificacion
        FROM historial_congelaciones h
        JOIN membresias m ON h.membresia_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        ORDER BY h.id DESC
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(QUERY)
        return [dict(r) for r in cur.fetchall()]


def exportar_congelamientos_csv(ruta_archivo: str) -> int:
    """
    Exporta la auditoría de congelamientos a un archivo CSV.
    """
    import csv

    historial = obtener_historial_congelaciones()

    with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Fecha", "Cédula", "Cliente", "Acción", "Justificación"])
        for h in historial:
            writer.writerow([
                h["fecha"],
                h["cedula"],
                h["cliente_nombre"],
                h["accion"],
                h["justificacion"]
            ])

    return len(historial)
