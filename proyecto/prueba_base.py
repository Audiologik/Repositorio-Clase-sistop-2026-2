# prueba_base.py

from imagen_fiunamfs import ImagenFiUnamFS


def main():
    fs = ImagenFiUnamFS("fiunamfs.img")

    fs.mostrar_superbloque()
    fs.imprimir_directorio()

    print("\n=== PRUEBA: COPIAR ARCHIVO LOCAL HACIA FIUNAMFS ===")

    with open("prueba.txt", "w") as archivo:
        archivo.write("Este archivo fue creado desde Ubuntu y copiado al FiUnamFS.\n")

    fs.copiar_a_fiunamfs("prueba.txt", "prueba.txt")
    print("Archivo prueba.txt copiado hacia FiUnamFS.")

    fs.imprimir_directorio()

    print("\n=== PRUEBA: EXTRAER ARCHIVO NUEVO ===")

    fs.extraer_archivo("prueba.txt", "prueba_extraida.txt")
    print("Archivo prueba.txt extraído como prueba_extraida.txt.")

    print("\n=== PRUEBA: ELIMINAR ARCHIVO ===")

    fs.eliminar_archivo("prueba.txt")
    print("Archivo prueba.txt eliminado de FiUnamFS.")

    fs.imprimir_directorio()

    fs.cerrar()


if __name__ == "__main__":
    main()