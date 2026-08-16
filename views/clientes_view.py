"""
clientes_view.py — Gestión de Clientes del gym (conectado a SQLite).

Flujo:
  1. Al montarse, carga los clientes con obtener_clientes() y rellena el DataTable.
  2. Barra de búsqueda filtra en tiempo real usando buscar_clientes().
  3. Al registrar, valida los campos, llama a crear_cliente(), recarga la tabla,
     limpia el formulario y muestra un SnackBar de éxito.
  4. El botón 'Enrolar Huella' en cada fila es un placeholder (TODO: ENROLL HOOK).
  5. El botón de eliminar llama a eliminar_cliente() con ON DELETE CASCADE en la BD.

Compatibilidad: Flet 0.86+ | sqlite3 (stdlib)
"""

import flet as ft
import sqlite3

from database.db_manager import (
    crear_cliente, obtener_clientes, buscar_clientes, eliminar_cliente, actualizar_cliente
)


def ClientesView() -> ft.Control:
    """
    Vista de Clientes con CRUD conectado a la BD y búsqueda en tiempo real.
    """

    _bg     = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _border = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    _fbg    = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _fbrd   = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _hdr_bg = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)

    # ── Campos del formulario ──────────────────────────────────────
    cedula_field = ft.TextField(
        hint_text="Cédula / DNI",
        prefix_icon=ft.Icons.BADGE_ROUNDED,
        border_radius=10, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        width=160, height=46,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
    )
    nombre_field = ft.TextField(
        hint_text="Nombre completo",
        prefix_icon=ft.Icons.PERSON_ROUNDED,
        border_radius=10, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        height=46, expand=True,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
    )
    telefono_field = ft.TextField(
        hint_text="Teléfono",
        prefix_icon=ft.Icons.PHONE_ROUNDED,
        keyboard_type=ft.KeyboardType.PHONE,
        border_radius=10, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        width=160, height=46,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
    )
    error_label = ft.Text("", size=12, color=ft.Colors.RED_400, visible=False)

    # ── Barra de búsqueda ──────────────────────────────────────────
    search_field = ft.TextField(
        hint_text="Buscar por nombre o cédula...",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        border_radius=12, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        height=46, expand=True,
        content_padding=ft.Padding(left=16, top=0, right=16, bottom=0),
    )

    # ── DataTable ──────────────────────────────────────────────────
    tabla_clientes = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cédula",    size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Nombre",    size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Teléfono",  size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Registro",  size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Acciones",  size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=_hdr_bg,
        border_radius=12,
        data_row_max_height=56,
        expand=True,
    )
    table_body = ft.Column(expand=True)

    # ── Helpers ────────────────────────────────────────────────────
    def _show_snack(page: ft.Page, msg: str, color):
        snack = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.with_opacity(0.92, color),
            duration=3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def _build_rows(filas_data, page):
        filas = []
        for c in filas_data:
            cid      = c["id"]
            cedula   = c["cedula"]
            nombre   = c["nombre"]
            telefono = c["telefono"] or "—"
            fecha    = (c["fecha_registro"] or "")[:10]   # solo la fecha

            def _on_enroll(e, cname=nombre):
                # TODO: ENROLL HOOK → iniciar captura de huella
                _show_snack(e.page, f"[Placeholder] Enrolamiento biométrico para {cname}.", ft.Colors.CYAN_900)

            def _on_delete(e, pid=cid, pname=nombre):
                def _confirm(e2):
                    dialog.open = False
                    e2.page.update()
                    eliminar_cliente(pid)
                    _refresh(e2.page)
                    _show_snack(e2.page, f"Cliente '{pname}' eliminado.", ft.Colors.ORANGE_900)

                def _cancel(e2):
                    dialog.open = False
                    e2.page.update()

                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Confirmar Eliminación", weight=ft.FontWeight.BOLD),
                    content=ft.Text(f"¿Estás seguro de que deseas eliminar al cliente '{pname}'?"),
                    actions=[
                        ft.TextButton("Cancelar", on_click=_cancel),
                        ft.TextButton("Eliminar", on_click=_confirm, style=ft.ButtonStyle(color=ft.Colors.RED_400)),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    bgcolor="#1A1D24",
                )
                e.page.overlay.append(dialog)
                dialog.open = True
                e.page.update()

            def _on_edit(e, pid=cid, curr_cedula=cedula, curr_nombre=nombre, curr_telefono=telefono):
                edit_cedula = ft.TextField(label="Cédula", value=curr_cedula, border_radius=8, bgcolor=_fbg, border_color=_fbrd, color=ft.Colors.WHITE)
                edit_nombre = ft.TextField(label="Nombre", value=curr_nombre, border_radius=8, bgcolor=_fbg, border_color=_fbrd, color=ft.Colors.WHITE)
                edit_telefono = ft.TextField(label="Teléfono", value=curr_telefono if curr_telefono != "—" else "", border_radius=8, bgcolor=_fbg, border_color=_fbrd, color=ft.Colors.WHITE)
                
                def _save(e2):
                    try:
                        actualizar_cliente(pid, edit_cedula.value, edit_nombre.value, edit_telefono.value)
                        dialog.open = False
                        _refresh(e2.page)
                        _show_snack(e2.page, f"Cliente '{edit_nombre.value}' actualizado.", ft.Colors.GREEN_900)
                    except sqlite3.Error as ex:
                        _show_snack(e2.page, f"Error al actualizar: {ex}", ft.Colors.RED_900)

                def _cancel(e2):
                    dialog.open = False
                    e2.page.update()

                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Editar Cliente", weight=ft.FontWeight.BOLD),
                    content=ft.Column([edit_cedula, edit_nombre, edit_telefono], tight=True, spacing=10),
                    actions=[
                        ft.TextButton("Cancelar", on_click=_cancel),
                        ft.TextButton("Guardar", on_click=_save, style=ft.ButtonStyle(color=ft.Colors.CYAN_400)),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    bgcolor="#1A1D24",
                )
                e.page.overlay.append(dialog)
                dialog.open = True
                e.page.update()

            acciones = ft.Row(
                controls=[
                    ft.IconButton(
                        ft.Icons.FINGERPRINT,
                        icon_color=ft.Colors.CYAN_400,
                        icon_size=18,
                        tooltip="Enrolar Huella (placeholder)",
                        on_click=_on_enroll,
                    ),
                    ft.IconButton(
                        ft.Icons.EDIT_ROUNDED,
                        icon_color=ft.Colors.ORANGE_400,
                        icon_size=18,
                        tooltip="Editar cliente",
                        on_click=_on_edit,
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_color=ft.Colors.RED_400,
                        icon_size=18,
                        tooltip="Eliminar cliente",
                        on_click=_on_delete,
                    ),
                ],
                spacing=0,
            )

            filas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(cedula,   color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(nombre,   color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(telefono, color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(fecha,    color=ft.Colors.WHITE54, size=12)),
                    ft.DataCell(acciones),
                ])
            )

        tabla_clientes.rows = filas

        if filas:
            table_body.controls = [tabla_clientes]
        else:
            table_body.controls = [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=52, color=ft.Colors.WHITE24),
                            ft.Text("No hay clientes registrados.", size=14, color=ft.Colors.WHITE38,
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    ),
                    padding=ft.Padding(left=0, top=40, right=0, bottom=40),
                    alignment=ft.Alignment(0, 0),
                )
            ]

    def _refresh(page: ft.Page):
        q = (search_field.value or "").strip()
        data = buscar_clientes(q) if q else obtener_clientes()
        _build_rows(data, page)
        page.update()

    def _clear_form():
        cedula_field.value   = ""
        nombre_field.value   = ""
        telefono_field.value = ""
        error_label.visible  = False
        cedula_field.border_color  = _fbrd
        nombre_field.border_color  = _fbrd
        telefono_field.border_color = _fbrd

    # ── Búsqueda en tiempo real ────────────────────────────────────
    def on_search(e: ft.ControlEvent):
        _refresh(e.page)

    search_field.on_change = on_search

    # ── Registrar cliente ──────────────────────────────────────────
    def on_register(e: ft.ControlEvent):
        page    = e.page
        cedula  = (cedula_field.value  or "").strip()
        nombre  = (nombre_field.value  or "").strip()
        telefono = (telefono_field.value or "").strip()

        has_error = False
        for field, val in [(cedula_field, cedula), (nombre_field, nombre)]:
            if not val:
                field.border_color = ft.Colors.RED_400
                has_error = True
            else:
                field.border_color = _fbrd

        if has_error:
            error_label.value   = "Cédula y Nombre son obligatorios."
            error_label.visible = True
            page.update()
            return

        try:
            crear_cliente(cedula, nombre, telefono)
            _clear_form()
            _refresh(page)
            _show_snack(page, f"✅  Cliente '{nombre}' registrado.", ft.Colors.GREEN_900)
        except sqlite3.IntegrityError:
            cedula_field.border_color = ft.Colors.RED_400
            error_label.value   = f"Ya existe un cliente con cédula '{cedula}'."
            error_label.visible = True
            page.update()
        except sqlite3.Error as ex:
            error_label.value   = f"Error en BD: {ex}"
            error_label.visible = True
            page.update()

    # ── Botones de acción superior ─────────────────────────────────
    register_btn = ft.Button(
        "Registrar Cliente",
        icon=ft.Icons.PERSON_ADD_ROUNDED,
        on_click=on_register,
        bgcolor=ft.Colors.CYAN_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    enroll_btn = ft.Button(
        "Enrolar Huella",
        icon=ft.Icons.FINGERPRINT,
        style=ft.ButtonStyle(
            color=ft.Colors.CYAN_400,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.CYAN_400),
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.4, ft.Colors.CYAN_400)),
            padding=ft.Padding(left=18, top=12, right=18, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    # ── Formulario ─────────────────────────────────────────────────
    form_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Registrar Cliente", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row(controls=[cedula_field, nombre_field, telefono_field], spacing=10),
                error_label,
                ft.Row(controls=[register_btn], alignment=ft.MainAxisAlignment.END),
            ],
            spacing=8,
        ),
        padding=ft.Padding(left=20, top=18, right=20, bottom=18),
        border_radius=14,
        bgcolor=_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
            bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
        ),
    )

    # ── Sección tabla ──────────────────────────────────────────────
    table_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PEOPLE_ALT_ROUNDED, size=18, color=ft.Colors.CYAN_400),
                        ft.Text("Clientes registrados", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                        ft.Container(expand=True),
                        enroll_btn,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row(controls=[search_field], spacing=10),
                ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                table_body,
            ],
            expand=True,
        ),
        padding=ft.Padding(left=20, top=18, right=20, bottom=18),
        border_radius=14,
        bgcolor=_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
            bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
        ),
        expand=True,
    )

    # ── Carga inicial (sin page) ───────────────────────────────────
    _build_rows(obtener_clientes(), None)

    return ft.Column(
        controls=[
            ft.Text("Membresías", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Clientes", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            form_container,
            ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
            table_container,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
