# trabajador.py

import threading
import queue


class TrabajadorFS:
    def __init__(self, sistema_archivos):
        self.fs = sistema_archivos

        # Cola de tareas que manda la interfaz
        self.tareas = queue.Queue()

        # Cola de respuestas que recibe la interfaz
        self.respuestas = queue.Queue()

        self.activo = True

        self.hilo = threading.Thread(
            target=self._procesar_tareas,
            daemon=True
        )

        self.hilo.start()

    def enviar_tarea(self, accion, datos=None):
        if datos is None:
            datos = {}

        self.tareas.put((accion, datos))

    def obtener_respuesta(self):
        try:
            return self.respuestas.get_nowait()
        except queue.Empty:
            return None

    def detener(self):
        self.activo = False
        self.tareas.put(("salir", {}))

    def _procesar_tareas(self):
        while self.activo:
            accion, datos = self.tareas.get()

            try:
                if accion == "listar":
                    archivos = self.fs.listar_archivos()

                    resultado = []
                    for archivo in archivos:
                        resultado.append({
                            "nombre": archivo.nombre,
                            "tamanio": archivo.tamanio,
                            "cluster": archivo.cluster_inicial,
                            "creacion": archivo.fecha_creacion,
                            "modificacion": archivo.fecha_modificacion
                        })

                    self.respuestas.put(("listar_ok", resultado))

                elif accion == "extraer":
                    nombre_fs = datos["nombre_fs"]
                    ruta_salida = datos["ruta_salida"]

                    self.fs.extraer_archivo(nombre_fs, ruta_salida)

                    self.respuestas.put((
                        "operacion_ok",
                        f"Archivo '{nombre_fs}' extraído correctamente."
                    ))

                elif accion == "copiar":
                    ruta_local = datos["ruta_local"]
                    nombre_fs = datos["nombre_fs"]

                    self.fs.copiar_a_fiunamfs(ruta_local, nombre_fs)

                    self.respuestas.put((
                        "operacion_ok",
                        f"Archivo '{nombre_fs}' copiado correctamente al FiUnamFS."
                    ))

                elif accion == "eliminar":
                    nombre_fs = datos["nombre_fs"]

                    self.fs.eliminar_archivo(nombre_fs)

                    self.respuestas.put((
                        "operacion_ok",
                        f"Archivo '{nombre_fs}' eliminado correctamente."
                    ))

                elif accion == "espacio":
                    libres, bytes_libres = self.fs.calcular_espacio_disponible()

                    self.respuestas.put((
                        "espacio_ok",
                        {
                            "clusters_libres": libres,
                            "bytes_libres": bytes_libres
                        }
                    ))

                elif accion == "salir":
                    break

            except Exception as e:
                self.respuestas.put(("error", str(e)))