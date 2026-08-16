"""
serial_manager.py
-----------------
Módulo de hardware para el control del torniquete físico vía puerto serial.

Responsabilidad única: enviar la señal de apertura (byte b'1') al
microcontrolador (Arduino, ESP32, etc.) conectado a un puerto COM.

Uso típico:
    from hardware.serial_manager import TorniqueteController

    ctrl = TorniqueteController()
    ok, msg = ctrl.abrir_torniquete("COM3")
    if ok:
        print("Torniquete abierto correctamente")
    else:
        print(f"Error de hardware: {msg}")

Dependencia externa:
    pip install pyserial

Seguridad:
    - Nunca lanza excepciones hacia el caller: todos los errores se capturan
      internamente y se retorna (False, mensaje_de_error).
    - La conexión siempre se cierra en el bloque finally, aunque el envío falle.
"""

import logging

logger = logging.getLogger(__name__)


class TorniqueteController:
    """
    Controlador del torniquete físico mediante puerto serial RS-232 / USB-TTL.

    El protocolo es intencionalmente simple:
        - Baud rate : 9600
        - Timeout   : 1 segundo
        - Señal     : byte único b'1'  → abrir torniquete
    """

    BAUD_RATE: int = 9600
    TIMEOUT_S: float = 1.0
    SEÑAL_APERTURA: bytes = b"1"

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def abrir_torniquete(self, puerto_com: str) -> tuple[bool, str]:
        """
        Abre una conexión serial con el microcontrolador, envía la señal
        de apertura y cierra la conexión inmediatamente.

        Args:
            puerto_com: Nombre del puerto (ej. 'COM3' en Windows,
                        '/dev/ttyUSB0' en Linux).

        Returns:
            tuple[bool, str]:
                - (True,  "OK")             → señal enviada correctamente.
                - (False, mensaje_de_error) → fallo; la app NO se cae.
        """
        if not puerto_com or not puerto_com.strip():
            msg = "Puerto COM no configurado. Ve a Configuración y guarda el puerto."
            logger.warning("[SERIAL] %s", msg)
            return False, msg

        puerto_com = puerto_com.strip().upper()
        conn = None

        try:
            import serial  # import tardío → si pyserial no está instalado,
                           # solo falla al llamar esta función, no al importar el módulo.

            logger.info("[SERIAL] Conectando a %s @ %d baud…", puerto_com, self.BAUD_RATE)

            conn = serial.Serial(
                port=puerto_com,
                baudrate=self.BAUD_RATE,
                timeout=self.TIMEOUT_S,
            )

            conn.write(self.SEÑAL_APERTURA)
            logger.info("[SERIAL] ✅ Señal b'1' enviada a %s", puerto_com)
            return True, "OK"

        except ModuleNotFoundError:
            msg = "Librería 'pyserial' no instalada. Ejecuta: pip install pyserial"
            logger.error("[SERIAL] %s", msg)
            return False, msg

        except Exception as exc:  # SerialException, PermissionError, OSError, etc.
            msg = f"{type(exc).__name__}: {exc}"
            logger.error("[SERIAL] ❌ Error en %s → %s", puerto_com, msg)
            return False, msg

        finally:
            if conn is not None:
                try:
                    conn.close()
                    logger.debug("[SERIAL] Puerto %s cerrado.", puerto_com)
                except Exception:
                    pass  # ignorar errores al cerrar


# ── Ejecución directa para pruebas rápidas ───────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")

    puerto = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    ctrl   = TorniqueteController()
    ok, mensaje = ctrl.abrir_torniquete(puerto)

    if ok:
        print(f"✅  Torniquete abierto en {puerto}")
    else:
        print(f"❌  Error: {mensaje}")
