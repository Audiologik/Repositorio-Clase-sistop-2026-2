# imagen_fiunamfs.py

import os
import struct
import threading
import math
import time

from config_fiunamfs import (
    OFFSET_NOMBRE_FS,
    OFFSET_VERSION,
    OFFSET_ETIQUETA,
    OFFSET_TAM_CLUSTER,
    OFFSET_CLUSTERS_DIRECTORIO,
    OFFSET_CLUSTERS_TOTALES,
    NOMBRE_FS_ESPERADO,
    VERSIONES_VALIDAS,
    CLUSTER_DIRECTORIO_INICIO,
    TAM_ENTRADA_DIRECTORIO
)

from registro_directorio import RegistroDirectorio
from bitacora import BitacoraFS


class ImagenFiUnamFS:
    def __init__(self, ruta_imagen):
        if not os.path.exists(ruta_imagen):
            raise FileNotFoundError(f"No existe la imagen: {ruta_imagen}")

        self.ruta_imagen = ruta_imagen
        self.disco = open(ruta_imagen, "r+b")

        self.lock = threading.Lock()
        self.bitacora = BitacoraFS()

        self.nombre_fs = ""
        self.version = ""
        self.etiqueta = ""
        self.tam_cluster = 0
        self.clusters_directorio = 0
        self.clusters_totales = 0
        self.cluster_datos_inicio = 0

        self.cargar_superbloque()

    # ==========================================================
    # Métodos básicos de lectura
    # ==========================================================

    def leer_bytes(self, offset, cantidad):
        self.disco.seek(offset)
        return self.disco.read(cantidad)

    def escribir_bytes(self, offset, datos):
        self.disco.seek(offset)
        self.disco.write(datos)
        self.disco.flush()

    def leer_entero_32(self, offset):
        datos = self.leer_bytes(offset, 4)
        return struct.unpack("<I", datos)[0]

    def leer_cadena(self, offset, cantidad):
        return (
            self.leer_bytes(offset, cantidad)
            .decode("ascii", errors="ignore")
            .replace("\x00", "")
            .strip()
        )

    # ==========================================================
    # Superbloque
    # ==========================================================

    def cargar_superbloque(self):
        self.nombre_fs = self.leer_cadena(OFFSET_NOMBRE_FS, 8)
        self.version = self.leer_cadena(OFFSET_VERSION, 4)
        self.etiqueta = self.leer_cadena(OFFSET_ETIQUETA, 16)

        self.tam_cluster = self.leer_entero_32(OFFSET_TAM_CLUSTER)
        self.clusters_directorio = self.leer_entero_32(OFFSET_CLUSTERS_DIRECTORIO)
        self.clusters_totales = self.leer_entero_32(OFFSET_CLUSTERS_TOTALES)

        if self.nombre_fs != NOMBRE_FS_ESPERADO:
            raise ValueError("La imagen no corresponde a FiUnamFS.")

        if not any(v in self.version for v in VERSIONES_VALIDAS):
            raise ValueError(f"Versión no soportada: {self.version}")

        self.cluster_datos_inicio = (
            CLUSTER_DIRECTORIO_INICIO + self.clusters_directorio
        )

    def mostrar_superbloque(self):
        print("\n=== SUPERBLOQUE ===")
        print(f"Sistema de archivos : {self.nombre_fs}")
        print(f"Versión             : {self.version}")
        print(f"Etiqueta            : {self.etiqueta}")
        print(f"Tamaño cluster      : {self.tam_cluster}")
        print(f"Clusters directorio : {self.clusters_directorio}")
        print(f"Clusters totales    : {self.clusters_totales}")
        print(f"Inicio datos        : cluster {self.cluster_datos_inicio}")

    # ==========================================================
    # Directorio
    # ==========================================================

    def offset_directorio(self):
        return CLUSTER_DIRECTORIO_INICIO * self.tam_cluster

    def cantidad_entradas_directorio(self):
        bytes_directorio = self.clusters_directorio * self.tam_cluster
        return bytes_directorio // TAM_ENTRADA_DIRECTORIO

    def leer_registros(self):
        registros = []

        inicio = self.offset_directorio()
        total = self.cantidad_entradas_directorio()

        for indice in range(total):
            offset = inicio + indice * TAM_ENTRADA_DIRECTORIO
            datos = self.leer_bytes(offset, TAM_ENTRADA_DIRECTORIO)
            registros.append(RegistroDirectorio(datos, indice))

        return registros

    def listar_archivos(self):
        archivos = []

        with self.lock:
            for registro in self.leer_registros():
                if registro.es_archivo_valido():
                    archivos.append(registro)

        return archivos

    def imprimir_directorio(self):
        print("\n=== DIRECTORIO ===")

        archivos = self.listar_archivos()

        if not archivos:
            print("No hay archivos registrados.")
            return

        for archivo in archivos:
            print(f"\nArchivo #{archivo.indice}")
            print(f"Nombre       : {archivo.nombre}")
            print(f"Tamaño       : {archivo.tamanio} bytes")
            print(f"Cluster ini  : {archivo.cluster_inicial}")
            print(f"Creación     : {archivo.fecha_creacion}")
            print(f"Modificación : {archivo.fecha_modificacion}")

    def buscar_archivo(self, nombre):
        for registro in self.leer_registros():
            if registro.es_archivo_valido() and registro.nombre == nombre:
                return registro
        return None

    # ==========================================================
    # Operaciones básicas
    # ==========================================================

    def extraer_archivo(self, nombre_fs, ruta_salida):
        with self.lock:
            registro = self.buscar_archivo(nombre_fs)

            if registro is None:
                raise FileNotFoundError(f"No existe el archivo en FiUnamFS: {nombre_fs}")

            offset_datos = registro.cluster_inicial * self.tam_cluster
            contenido = self.leer_bytes(offset_datos, registro.tamanio)

            with open(ruta_salida, "wb") as salida:
                salida.write(contenido)

            self.bitacora.registrar_lectura(
                f"Se extrajo {nombre_fs} hacia {ruta_salida}"
            )

    def offset_entrada_directorio(self, indice):
        return self.offset_directorio() + indice * TAM_ENTRADA_DIRECTORIO

    def buscar_entrada_libre(self):
        registros = self.leer_registros()

        for registro in registros:
            if registro.esta_libre():
                return registro.indice

        return None

    def obtener_clusters_ocupados(self):
        ocupados = set()

        for registro in self.leer_registros():
            if registro.es_archivo_valido():
                clusters_usados = self.clusters_ocupados_por_archivo(registro)

                for cluster in range(
                    registro.cluster_inicial,
                    registro.cluster_inicial + clusters_usados
                ):
                    ocupados.add(cluster)

        return ocupados

    def buscar_bloque_libre(self, clusters_necesarios):
        ocupados = self.obtener_clusters_ocupados()

        cluster_actual = self.cluster_datos_inicio

        while cluster_actual <= self.clusters_totales - clusters_necesarios:
            disponible = True

            for i in range(clusters_necesarios):
                if cluster_actual + i in ocupados:
                    disponible = False
                    break

            if disponible:
                return cluster_actual

            cluster_actual += 1

        return None

    def eliminar_archivo(self, nombre_fs):
        with self.lock:
            registro = self.buscar_archivo(nombre_fs)

            if registro is None:
                raise FileNotFoundError(f"No existe el archivo en FiUnamFS: {nombre_fs}")

            offset = self.offset_entrada_directorio(registro.indice)

            entrada_vacia = bytearray(TAM_ENTRADA_DIRECTORIO)
            entrada_vacia[0:1] = b"/"
            entrada_vacia[1:16] = b"###############"

            self.escribir_bytes(offset, entrada_vacia)

            self.bitacora.registrar_eliminacion(
                f"Se eliminó {nombre_fs} del FiUnamFS"
            )

    def copiar_a_fiunamfs(self, ruta_local, nombre_fs=None):
        with self.lock:
            if not os.path.exists(ruta_local):
                raise FileNotFoundError(f"No existe el archivo local: {ruta_local}")

            if nombre_fs is None:
                nombre_fs = os.path.basename(ruta_local)

            try:
                nombre_fs.encode("ascii")
            except UnicodeEncodeError:
                raise ValueError("El nombre debe usar solamente caracteres ASCII.")

            if len(nombre_fs) > 15:
                raise ValueError("El nombre del archivo no puede superar 15 caracteres.")

            if self.buscar_archivo(nombre_fs) is not None:
                raise ValueError(f"Ya existe un archivo llamado {nombre_fs} en FiUnamFS.")

            indice_libre = self.buscar_entrada_libre()

            if indice_libre is None:
                raise RuntimeError("No hay entradas libres en el directorio.")

            tamanio = os.path.getsize(ruta_local)
            clusters_necesarios = math.ceil(tamanio / self.tam_cluster)

            cluster_inicial = self.buscar_bloque_libre(clusters_necesarios)

            if cluster_inicial is None:
                raise RuntimeError("No hay espacio contiguo suficiente en FiUnamFS.")

            with open(ruta_local, "rb") as archivo:
                contenido = archivo.read()

            offset_datos = cluster_inicial * self.tam_cluster
            self.escribir_bytes(offset_datos, contenido)

            nueva_entrada = bytearray(TAM_ENTRADA_DIRECTORIO)

            nueva_entrada[0:1] = b"-"
            nueva_entrada[1:16] = nombre_fs.ljust(15).encode("ascii")
            nueva_entrada[16:20] = struct.pack("<I", tamanio)
            nueva_entrada[20:24] = struct.pack("<I", cluster_inicial)

            fecha_actual = time.strftime("%Y%m%d%H%M%S").encode("ascii")

            nueva_entrada[30:44] = fecha_actual
            nueva_entrada[50:64] = fecha_actual

            offset_entrada = self.offset_entrada_directorio(indice_libre)
            self.escribir_bytes(offset_entrada, nueva_entrada)

            self.bitacora.registrar_escritura(
                f"Se copió {ruta_local} como {nombre_fs}"
            )

    def clusters_ocupados_por_archivo(self, registro):
        return math.ceil(registro.tamanio / self.tam_cluster)
    
    def calcular_espacio_disponible(self):
        ocupados = self.obtener_clusters_ocupados()

        total_clusters_datos = self.clusters_totales - self.cluster_datos_inicio
        clusters_usados = len(ocupados)

        clusters_libres = total_clusters_datos - clusters_usados
        bytes_libres = clusters_libres * self.tam_cluster

        return clusters_libres, bytes_libres

    def cerrar(self):
        self.disco.close()