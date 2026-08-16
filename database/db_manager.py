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
                              CHECK (estado IN ('ACTIVA', 'VENCIDA', 'SUSPENDIDA'))
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


def obtener_clientes() -> list[sqlite3.Row]:
    """
    Retorna todos los clientes ordenados por nombre.

    Returns:
        list[sqlite3.Row]: Cada fila tiene columnas:
                           row['id'], row['cedula'], row['nombre'],
                           row['telefono'], row['fecha_registro']
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cedula, nombre, telefono, fecha_registro "
            "FROM clientes ORDER BY nombre"
        )
        return cur.fetchall()


def buscar_clientes(query: str) -> list[sqlite3.Row]:
    """
    Busca clientes cuyo nombre o cédula contengan el texto dado.

    Args:
        query: Texto a buscar (insensible a mayúsculas).

    Returns:
        list[sqlite3.Row]: Clientes que coinciden, ordenados por nombre.
    """
    pattern = f"%{query}%"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cedula, nombre, telefono, fecha_registro "
            "FROM clientes WHERE nombre LIKE ? OR cedula LIKE ? ORDER BY nombre",
            (pattern, pattern),
        )
        return cur.fetchall()

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


def crear_membresia(cliente_id: int, plan_id: int) -> dict:
    """
    Crea una membresía activa calculando las fechas según el plan.

    Args:
        cliente_id: ID del cliente.
        plan_id: ID del plan.

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

        # b. Calcular fecha_inicio (fecha actual)
        fecha_inicio_obj = datetime.now().date()
        fecha_inicio = fecha_inicio_obj.strftime("%Y-%m-%d")

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


def obtener_historial_membresias() -> list[dict]:
    """
    Devuelve las últimas renovaciones usando JOIN.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
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
            ORDER BY m.id DESC
            LIMIT 50
            """
        )
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
        
        # b. Buscar la membresía activa más reciente
        cur.execute(
            """
            SELECT id, fecha_vencimiento, estado 
            FROM membresias 
            WHERE cliente_id = ? AND estado = 'ACTIVA'
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

