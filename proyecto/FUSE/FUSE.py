#!/usr/bin/env python3
# fuse_fiunamfs.py

import os
import sys
import stat
import time
import tempfile

from errno import ENOENT, EEXIST

from fuse import FUSE, Operations, FuseOSError

from imagen_fiunamfs import ImagenFiUnamFS


class MontajeFiUnamFS(Operations):
    def __init__(self, ruta_imagen):
        self.fs = ImagenFiUnamFS(ruta_imagen)

        # Aquí guardamos temporalmente archivos que se están escribiendo.
        self.archivos_abiertos = {}

    # ==========================================================
    # Utilidades
    # ==========================================================

    def _nombre_desde_path(self, path):
        return path.lstrip("/")

    def _buscar(self, path):
        nombre = self._nombre_desde_path(path)

        if nombre == "":
            return None

        with self.fs.lock:
            return self.fs.buscar_archivo(nombre)

    # ==========================================================
    # Atributos de archivos/directorios
    # ==========================================================

    def getattr(self, path, fh=None):
        # Directorio raíz del montaje
        if path == "/":
            return {
                "st_mode": stat.S_IFDIR | 0o755,
                "st_nlink": 2,
                "st_size": 0,
                "st_ctime": time.time(),
                "st_mtime": time.time(),
                "st_atime": time.time()
            }

        registro = self._buscar(path)

        if registro is None:
            raise FuseOSError(ENOENT)

        return {
            "st_mode": stat.S_IFREG | 0o644,
            "st_nlink": 1,
            "st_size": registro.tamanio,
            "st_ctime": time.time(),
            "st_mtime": time.time(),
            "st_atime": time.time()
        }

    # ==========================================================
    # Listar directorio
    # ==========================================================

    def readdir(self, path, fh):
        if path != "/":
            raise FuseOSError(ENOENT)

        archivos = self.fs.listar_archivos()
        nombres = [archivo.nombre for archivo in archivos]

        return [".", ".."] + nombres

    # ==========================================================
    # Abrir y leer archivos
    # ==========================================================

    def open(self, path, flags):
        registro = self._buscar(path)

        if registro is None:
            raise FuseOSError(ENOENT)

        return 0

    def read(self, path, size, offset, fh):
        registro = self._buscar(path)

        if registro is None:
            raise FuseOSError(ENOENT)

        if offset >= registro.tamanio:
            return b""

        cantidad = min(size, registro.tamanio - offset)

        with self.fs.lock:
            posicion = registro.cluster_inicial * self.fs.tam_cluster + offset
            self.fs.disco.seek(posicion)
            datos = self.fs.disco.read(cantidad)

            self.fs.bitacora.registrar_lectura(
                f"Lectura desde FUSE: {registro.nombre}"
            )

        return datos

    # ==========================================================
    # Crear y escribir archivos
    # ==========================================================

    def create(self, path, mode, fi=None):
        nombre = self._nombre_desde_path(path)

        if self._buscar(path) is not None:
            raise FuseOSError(EEXIST)

        self.archivos_abiertos[nombre] = bytearray()

        return 0

    def mknod(self, path, mode, dev):
        nombre = self._nombre_desde_path(path)

        if self._buscar(path) is not None:
            raise FuseOSError(EEXIST)

        self.archivos_abiertos[nombre] = bytearray()

        return 0

    def truncate(self, path, length, fh=None):
        nombre = self._nombre_desde_path(path)

        if nombre not in self.archivos_abiertos:
            registro = self._buscar(path)

            if registro is None:
                self.archivos_abiertos[nombre] = bytearray()
            else:
                with self.fs.lock:
                    posicion = registro.cluster_inicial * self.fs.tam_cluster
                    self.fs.disco.seek(posicion)
                    contenido = self.fs.disco.read(registro.tamanio)

                self.archivos_abiertos[nombre] = bytearray(contenido)

        buffer = self.archivos_abiertos[nombre]

        if length < len(buffer):
            del buffer[length:]
        elif length > len(buffer):
            buffer.extend(b"\x00" * (length - len(buffer)))

        return 0

    def flush(self, path, fh):
        return 0

    def utimens(self, path, times=None):
        return 0


    def write(self, path, data, offset, fh):
        nombre = self._nombre_desde_path(path)

        if nombre not in self.archivos_abiertos:
            self.archivos_abiertos[nombre] = bytearray()

        buffer = self.archivos_abiertos[nombre]

        fin = offset + len(data)

        if fin > len(buffer):
            buffer.extend(b"\x00" * (fin - len(buffer)))

        buffer[offset:fin] = data

        return len(data)

    def release(self, path, fh):
        nombre = self._nombre_desde_path(path)

        if nombre in self.archivos_abiertos:
            contenido = self.archivos_abiertos[nombre]

            fd, ruta_temporal = tempfile.mkstemp()

            try:
                with os.fdopen(fd, "wb") as tmp:
                    tmp.write(contenido)

                # Si ya existía, lo eliminamos antes de guardar la nueva versión.
                # Esto permite sobrescritura sencilla.
                if self.fs.buscar_archivo(nombre) is not None:
                    self.fs.eliminar_archivo(nombre)

                self.fs.copiar_a_fiunamfs(ruta_temporal, nombre)

            finally:
                if os.path.exists(ruta_temporal):
                    os.remove(ruta_temporal)

                del self.archivos_abiertos[nombre]

        return 0

    # ==========================================================
    # Eliminar archivos
    # ==========================================================

    def unlink(self, path):
        nombre = self._nombre_desde_path(path)

        if self._buscar(path) is None:
            raise FuseOSError(ENOENT)

        self.fs.eliminar_archivo(nombre)

        return 0

    # ==========================================================
    # Renombrar archivo
    # ==========================================================

    def rename(self, old, new):
        raise FuseOSError(ENOENT)

    def destroy(self, path):
        self.fs.cerrar()


def main():
    if len(sys.argv) != 3:
        print("Uso:")
        print("  python3 fuse_fiunamfs.py <imagen.img> <carpeta_montaje>")
        sys.exit(1)

    ruta_imagen = sys.argv[1]
    punto_montaje = sys.argv[2]

    if not os.path.exists(ruta_imagen):
        print(f"No existe la imagen: {ruta_imagen}")
        sys.exit(1)

    if not os.path.isdir(punto_montaje):
        print(f"No existe la carpeta de montaje: {punto_montaje}")
        sys.exit(1)

    print("[INFO] Montando FiUnamFS...")
    print("[INFO] Para desmontar usa: fusermount -u", punto_montaje)

    FUSE(
        MontajeFiUnamFS(ruta_imagen),
        punto_montaje,
        foreground=True,
        nothreads=True
    )


if __name__ == "__main__":
    main()