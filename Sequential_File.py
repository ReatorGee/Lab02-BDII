import struct
import os
import csv
import time
import random
from datetime import datetime, timedelta

FORMAT = "<i30sif10si1si"
RECORD_SIZE = struct.calcsize(FORMAT)

class Venta:
    def __init__(self, id, nombre, cantidad, precio, fechaVenta, indice=-1, filetype='d', activo=1):
        self.id = id
        self.nombre = nombre[:30].ljust(30)
        self.cantidad = cantidad
        self.precio = precio
        self.fechaVenta = fechaVenta[:10].ljust(10)
        self.indice = indice
        self.filetype = filetype
        self.activo = activo

    def to_bytes(self):
        return struct.pack(
            FORMAT,
            self.id,
            self.nombre.encode('latin1'),
            self.cantidad,
            self.precio,
            self.fechaVenta.encode('latin1'),
            int(self.indice),
            self.filetype.encode('latin1'),
            self.activo
        )

    @staticmethod
    def from_bytes(data):
        id, nombre, cantidad, precio, fechaVenta, indice, filetype, activo = struct.unpack(FORMAT, data)
        return Venta(
            id,
            nombre.decode('latin1').strip(),
            cantidad,
            precio,
            fechaVenta.decode('latin1').strip(),
            indice,
            filetype.decode('latin1').strip(),
            activo
        )

class SequentialFile:
    def __init__(self, filename, auxfile, k):
        self.filename = filename
        self.auxfile = auxfile
        self.k = k  # límite del auxiliar
        if not os.path.exists(self.filename):
            open(self.filename, 'wb').close()
        if not os.path.exists(self.auxfile):
            open(self.auxfile, 'wb').close()

    def insert(self, record: Venta):
        inserted = False
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            pos = 0
            while True:
                current_pos = file.tell()
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not index_data or not data:
                    break

                index = struct.unpack('<i', index_data)[0]
                current = Venta.from_bytes(data)

                next_pos = file.tell()
                next_index_data = file.read(4)
                next_data = file.read(RECORD_SIZE)

                if not next_index_data or not next_data:
                    break

                next_index = struct.unpack('<i', next_index_data)[0]
                next_record = Venta.from_bytes(next_data)

                if current.id < record.id < next_record.id:
                    if self.k == 0:
                        self.rebuild()
                        self.insert(record)
                        return
                    else:
                        with open(self.auxfile, 'ab') as aux:
                            aux_index = aux.tell() // (4 + RECORD_SIZE)
                            aux.write(struct.pack('<i', -1))
                            aux.write(record.to_bytes())
                            # Actualizar punteros lógicos
                            current.indice = aux_index
                            current.filetype = 'a'
                            file.seek(current_pos + 4)  # después del índice
                            file.write(current.to_bytes())
                            self.k -= 1
                            inserted = True
                            break

                file.seek(next_pos)

            if not inserted:
                file.seek(0, os.SEEK_END)
                file.write(struct.pack('<i', -1))
                file.write(record.to_bytes())

    def rebuild(self):
        registros = []
        # Leer archivo principal
        with open(self.filename, 'rb') as file:
            while True:
                index_data = file.read(4)
                if not index_data:
                    break
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1:
                    registros.append(reg)

        # Leer archivo auxiliar
        with open(self.auxfile, 'rb') as aux:
            while True:
                index_data = aux.read(4)
                if not index_data:
                    break
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1:
                    registros.append(reg)

        # Ordenar registros
        registros.sort(key=lambda r: r.id)

        # Reescribir archivo principal
        with open(self.filename, 'wb') as file:
            for reg in registros:
                reg.indice = -1
                reg.filetype = 'd'
                file.write(struct.pack('<i', -1))
                file.write(reg.to_bytes())

        # Vaciar auxiliar
        open(self.auxfile, 'wb').close()
        self.k = 10  # reinicia el contador del auxiliar a su valor máximo

                                    

    def search(self, id):
        with open(self.filename, 'rb') as file:
            while True:
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    return reg
                # Si hay un puntero al auxiliar, seguimos buscando
                if reg.indice != -1 and reg.filetype == 'a':
                    found = self._search_aux(id, reg.indice)
                    if found:
                        return found
        return None

    def _search_aux(self, id, start_index):
        with open(self.auxfile, 'rb') as aux:
            current_index = start_index
            while current_index != -1:
                pos = current_index * (4 + RECORD_SIZE)
                aux.seek(pos)
                index_data = aux.read(4)
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    return reg
                current_index = reg.indice if reg.filetype == 'a' else -1
        return None


    def delete(self, id):
        with open(self.filename, 'r+b') as file:
            while True:
                pos = file.tell()
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    reg.activo = 0
                    file.seek(pos + 4)
                    file.write(reg.to_bytes())
                    print(f"Registro con ID {id} eliminado del archivo principal.")
                    return True
                # Buscar en auxiliar si hay puntero
                if reg.indice != -1 and reg.filetype == 'a':
                    deleted = self._delete_aux(id, reg.indice)
                    if deleted:
                        return True
        print(f"Registro con ID {id} no encontrado.")
        return False

    def _delete_aux(self, id, start_index):
        with open(self.auxfile, 'r+b') as aux:
            current_index = start_index
            while current_index != -1:
                pos = current_index * (4 + RECORD_SIZE)
                aux.seek(pos)
                index_data = aux.read(4)
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    reg.activo = 0
                    aux.seek(pos + 4)
                    aux.write(reg.to_bytes())
                    print(f"Registro con ID {id} eliminado del archivo auxiliar.")
                    return True
                current_index = reg.indice if reg.filetype == 'a' else -1
        return False


    def search_range(self, min_id, max_id):
        resultados = []
        with open(self.filename, 'rb') as file:
            while True:
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1 and min_id <= reg.id <= max_id:
                    resultados.append(reg)
                # Buscar en auxiliar si hay puntero
                if reg.indice != -1 and reg.filetype == 'a':
                    aux_regs = self._search_aux_range(min_id, max_id, reg.indice)
                    resultados.extend(aux_regs)
        return resultados

    def _search_aux_range(self, min_id, max_id, start_index):
        encontrados = []
        with open(self.auxfile, 'rb') as aux:
            current_index = start_index
            while current_index != -1:
                pos = current_index * (4 + RECORD_SIZE)
                aux.seek(pos)
                index_data = aux.read(4)
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1 and min_id <= reg.id <= max_id:
                    encontrados.append(reg)
                current_index = reg.indice if reg.filetype == 'a' else -1
        return encontrados



def cargar_ventas_csv(ruta_csv):
    ventas = []
    with open(ruta_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            venta = Venta(
                int(row['ID de la venta']),
                row['Nombre producto'],
                int(row['Cantidad vendida']),
                float(row['Precio unitario']),
                row['Fecha de venta']
            )
            ventas.append(venta)
    return ventas


if os.path.exists("ventas.dat"):
    os.remove("ventas.dat")

def probar_tiempos_con_csv():
    # Eliminar archivos anteriores
    if os.path.exists("ventas_1000.dat"):
        os.remove("ventas_1000.dat")
    if os.path.exists("auxiliar_1000.dat"):
        os.remove("auxiliar_1000.dat")

    archivo_principal = "ventas_1000.dat"
    archivo_auxiliar = "auxiliar_1000.dat"
    sf = SequentialFile(archivo_principal, archivo_auxiliar, k=30)

    ventas = cargar_ventas_csv("sales_dataset.csv")
    print(f"\n⏱️ Midiendo tiempos con {len(ventas)} registros del CSV...")

    # Inserción
    t0 = time.time()
    for venta in ventas:
        sf.insert(venta)
    t_insert = (time.time() - t0) * 1000

    # Tomamos un ID del medio para buscar y eliminar
    target_id = ventas[500].id
    rango_min = ventas[300].id
    rango_max = ventas[700].id
    if rango_min > rango_max:
        rango_min, rango_max = rango_max, rango_min

    # Búsqueda
    t0 = time.time()
    resultado = sf.search(target_id)
    t_search = (time.time() - t0) * 1000

    # Búsqueda por rango
    t0 = time.time()
    resultados_rango = sf.search_range(rango_min, rango_max)
    t_range = (time.time() - t0) * 1000

    # Eliminación
    t0 = time.time()
    sf.delete(target_id)
    t_delete = (time.time() - t0) * 1000

    # Reconstrucción
    t0 = time.time()
    sf.rebuild()
    t_rebuild = (time.time() - t0) * 1000

    # Resultados
    print(f"\n📊 Resultados de tiempo con CSV real:")
    print(f"🟢 Inserción total de {len(ventas)} registros: {t_insert:.3f} ms")
    print(f"🔍 Búsqueda por ID ({target_id}): {t_search:.3f} ms")
    print(f"🔎 Búsqueda por rango ({rango_min}–{rango_max}): {t_range:.3f} ms")
    print(f"🗑 Eliminación por ID ({target_id}): {t_delete:.3f} ms")
    print(f"♻️ Reconstrucción completa: {t_rebuild:.3f} ms")

# Ejecutar prueba
probar_tiempos_con_csv()